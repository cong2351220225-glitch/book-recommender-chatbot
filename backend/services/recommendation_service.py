from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

from backend.core.config import (
    RECOMMENDATIONS_DIR,
    BOOKSHELVES_DIR,
    COMMUNITY_DB_PATH,
    CHROMA_PATH,
    COLLECTION_NAME,
)
from backend.core.database import get_books_df
from backend.routers.bookshelf_router import _load_user_bookshelf
from backend.routers.reading_router import _load_user_progress
from book_service import normalize_search_text, get_book_by_id

LOGGER = logging.getLogger(__name__)

RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)
_rec_lock = threading.Lock()


@dataclass
class RecommendationWeights:
    favorite: float = 3.0
    reading: float = 2.0
    completed: float = 1.2
    preferred_genre: float = 2.5
    preferred_author: float = 2.0
    same_genre: float = 2.0
    tags_overlap: float = 1.5
    same_author: float = 1.2
    semantic_vector: float = 2.5
    rating_bonus: float = 0.5
    liked_feedback_boost: float = 2.0
    max_per_genre_ratio: float = 0.4
    max_per_author_ratio: float = 0.3


DEFAULT_WEIGHTS = RecommendationWeights()


def sanitize_username(username: str) -> str:
    """Sanitize username to prevent path traversal attacks."""
    cleaned = str(username).strip()
    if not cleaned or not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
        raise ValueError("Tên người dùng không hợp lệ hoặc chứa ký tự đặc biệt nguy hiểm")
    return cleaned


def _get_user_file(username: str) -> Path:
    safe_name = sanitize_username(username)
    return RECOMMENDATIONS_DIR / f"{safe_name}.json"


def load_user_recommendation_data(username: str) -> dict[str, Any]:
    """Load user preferences, feedback and cached data with thread safety and corrupted json recovery."""
    file_path = _get_user_file(username)
    default_data: dict[str, Any] = {
        "username": username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "preferences": {
            "preferred_genres": [],
            "preferred_authors": [],
            "reading_goal": "",
        },
        "feedback": {},  # {book_id: {"liked": bool, "reason": str, "updated_at": str}}
        "cached_recommendations": {},
    }

    with _rec_lock:
        if not file_path.exists():
            return default_data
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return default_data
                data.setdefault("preferences", default_data["preferences"])
                data.setdefault("feedback", {})
                data.setdefault("cached_recommendations", {})
                return data
        except Exception as exc:
            LOGGER.warning("Corrupted recommendation file for user %s: %s. Re-initializing.", username, exc)
            return default_data


def save_user_recommendation_data(username: str, data: dict[str, Any]) -> None:
    """Save user recommendation data atomically and thread-safely."""
    file_path = _get_user_file(username)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with _rec_lock:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(file_path)


def update_user_preferences(
    username: str,
    preferred_genres: list[str],
    preferred_authors: list[str],
    reading_goal: str = "",
) -> dict[str, Any]:
    """Update user reading preferences."""
    data = load_user_recommendation_data(username)
    data["preferences"] = {
        "preferred_genres": [str(g).strip() for g in preferred_genres if str(g).strip()],
        "preferred_authors": [str(a).strip() for a in preferred_authors if str(a).strip()],
        "reading_goal": str(reading_goal).strip(),
    }
    save_user_recommendation_data(username, data)
    return data["preferences"]


def save_user_feedback(
    username: str,
    book_id: str,
    liked: bool | None,
    reason: str = "",
) -> dict[str, Any]:
    """
    Save user feedback for a recommended book.
    liked=True (Like), liked=False (Dislike), liked=None (Reset/Cancel Dislike).
    """
    cleaned_id = str(book_id).strip()
    if not cleaned_id or not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned_id):
        raise ValueError("Mã sách không hợp lệ")

    data = load_user_recommendation_data(username)
    feedback_dict = data.setdefault("feedback", {})

    if liked is None:
        # Reset / Hủy phản hồi
        if cleaned_id in feedback_dict:
            del feedback_dict[cleaned_id]
    else:
        feedback_dict[cleaned_id] = {
            "liked": bool(liked),
            "reason": str(reason).strip(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    save_user_recommendation_data(username, data)
    return feedback_dict.get(cleaned_id, {"liked": None, "message": "Feedback reset"})


# ---------------------------------------------------------------------------
# Semantic Vector Retrieval with ChromaDB (Offline & Zero-Quota Centroid)
# ---------------------------------------------------------------------------

def query_semantic_by_book_ids(
    base_book_ids: list[str],
    n_results: int = 15,
) -> dict[str, float]:
    """
    Query ChromaDB using pre-indexed vector embeddings of base_book_ids.
    Calculates the centroid embedding without making external Gemini API calls.
    Returns {book_id: similarity_score}.
    """
    valid_ids = [str(bid).strip() for bid in base_book_ids if str(bid).strip()]
    if not valid_ids:
        return {}

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)

        got = collection.get(ids=valid_ids, include=["embeddings"])
        embeddings = got.get("embeddings") if got else None
        if not embeddings or len(embeddings) == 0:
            return {}

        # Compute centroid (mean vector) across all base books
        dim = len(embeddings[0])
        centroid = [0.0] * dim
        for emb in embeddings:
            for i in range(dim):
                centroid[i] += emb[i]
        centroid = [val / len(embeddings) for val in centroid]

        query_res = collection.query(
            query_embeddings=[centroid],
            n_results=min(n_results, collection.count() or 1),
            include=["distances"],
        )

        if not query_res or not query_res.get("ids") or not query_res["ids"][0]:
            return {}

        book_ids = query_res["ids"][0]
        distances = query_res["distances"][0] if query_res.get("distances") and query_res["distances"][0] else [0.5] * len(book_ids)

        scores: dict[str, float] = {}
        for b_id, dist in zip(book_ids, distances):
            sim = max(0.0, min(1.0, 1.0 - (float(dist) / 2.0)))
            scores[str(b_id)] = sim
        return scores
    except Exception as exc:
        LOGGER.warning("ChromaDB centroid query skipped gracefully: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Recommendation Algorithms
# ---------------------------------------------------------------------------

def _extract_tags_set(tags_str: Any) -> set[str]:
    if not tags_str or pd.isna(tags_str):
        return set()
    return {
        normalize_search_text(t)
        for t in str(tags_str).replace(";", ",").split(",")
        if normalize_search_text(t)
    }


def _apply_diversity_filter(
    ranked_books: list[dict[str, Any]],
    limit: int,
    max_per_genre_ratio: float = 0.4,
    max_per_author_ratio: float = 0.3,
) -> list[dict[str, Any]]:
    """Ensure no single genre or author dominates the recommendations."""
    if not ranked_books or limit <= 0:
        return []

    max_per_genre = max(2, int(limit * max_per_genre_ratio))
    max_per_author = max(1, int(limit * max_per_author_ratio))

    genre_counts: dict[str, int] = {}
    author_counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    overflow: list[dict[str, Any]] = []

    for item in ranked_books:
        genre = str(item.get("genre", "Khác")).strip()
        author = str(item.get("author", "Khác")).strip()

        g_count = genre_counts.get(genre, 0)
        a_count = author_counts.get(author, 0)

        if g_count < max_per_genre and a_count < max_per_author:
            selected.append(item)
            genre_counts[genre] = g_count + 1
            author_counts[author] = a_count + 1
            if len(selected) >= limit:
                break
        else:
            overflow.append(item)

    # Only backfill if we couldn't reach the limit from all available diverse items
    if len(selected) < limit and overflow:
        for item in overflow:
            if len(selected) >= limit:
                break
            selected.append(item)

    return selected[:limit]


# ---------------------------------------------------------------------------
# Collaborative Filtering Matrix & Scoring
# ---------------------------------------------------------------------------

def build_user_interaction_matrix() -> dict[str, dict[str, float]]:
    """
    Build user-item interaction matrix from existing real user bookshelves, reviews and feedback.
    Weights:
      - Bookshelf favorite: 3.0
      - Bookshelf completed: 2.5
      - Bookshelf reading: 2.0
      - Review rating: (1..5 stars) -> 1.0..3.0
      - Recommendation liked: +1.0
    """
    matrix: dict[str, dict[str, float]] = {}

    # 1. Bookshelves
    if BOOKSHELVES_DIR.exists():
        for bf in BOOKSHELVES_DIR.glob("*.json"):
            u = bf.stem
            try:
                with open(bf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data.get("items", {})
                    items_iter = items.values() if isinstance(items, dict) else items
                    for it in items_iter:
                        bid = str(it.get("book_id", "")).strip()
                        if not bid:
                            continue
                        status = str(it.get("status", "favorite")).strip()
                        w = 3.0 if status == "favorite" else (2.5 if status == "completed" else 2.0)
                        if u not in matrix:
                            matrix[u] = {}
                        matrix[u][bid] = max(matrix[u].get(bid, 0.0), w)
            except Exception:
                pass

    # 2. SQLite reviews
    if COMMUNITY_DB_PATH.exists():
        try:
            conn = sqlite3.connect(COMMUNITY_DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT username, book_id, rating FROM reviews WHERE status = 'visible';")
            for u, b, r in cur.fetchall():
                u_str = str(u).strip()
                b_str = str(b).strip()
                if u_str and b_str:
                    rating_val = float(r) if r is not None else 3.0
                    w = (rating_val / 5.0) * 3.0
                    if u_str not in matrix:
                        matrix[u_str] = {}
                    matrix[u_str][b_str] = max(matrix[u_str].get(b_str, 0.0), w)
            conn.close()
        except Exception:
            pass

    # 3. Recommendation feedback
    if RECOMMENDATIONS_DIR.exists():
        for rf in RECOMMENDATIONS_DIR.glob("*.json"):
            u = rf.stem
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    fb = data.get("feedback", {})
                    for bid, val in fb.items():
                        bid_str = str(bid).strip()
                        if val.get("liked") is True and bid_str:
                            if u not in matrix:
                                matrix[u] = {}
                            matrix[u][bid_str] = matrix[u].get(bid_str, 0.0) + 1.0
            except Exception:
                pass

    return matrix


def compute_collaborative_filtering_scores(
    username: str,
    user_matrix: dict[str, dict[str, float]],
    excluded_bids: set[str],
    top_k_users: int = 15,
) -> dict[str, float]:
    """
    User-based Collaborative Filtering using Cosine Similarity.
    Cold-start safe: Returns empty dict if target user has no history or no neighbors.
    """
    if not username or username not in user_matrix:
        return {}

    target_interactions = user_matrix[username]
    if not target_interactions:
        return {}

    # Target user vector norm
    target_norm = math.sqrt(sum(v * v for v in target_interactions.values()))
    if target_norm == 0:
        return {}

    # Calculate similarity with all other users
    similarities: list[tuple[str, float]] = []
    for other_user, other_interactions in user_matrix.items():
        if other_user == username or not other_interactions:
            continue
        common_books = set(target_interactions.keys()) & set(other_interactions.keys())
        if not common_books:
            continue

        dot_product = sum(target_interactions[b] * other_interactions[b] for b in common_books)
        other_norm = math.sqrt(sum(v * v for v in other_interactions.values()))
        if other_norm > 0:
            sim = dot_product / (target_norm * other_norm)
            if sim > 0:
                similarities.append((other_user, sim))

    if not similarities:
        return {}

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_neighbors = similarities[:top_k_users]

    candidate_scores: dict[str, float] = {}
    sum_sims: dict[str, float] = {}

    for neighbor, sim in top_neighbors:
        for book_id, rating in user_matrix[neighbor].items():
            if book_id in target_interactions or book_id in excluded_bids:
                continue
            candidate_scores[book_id] = candidate_scores.get(book_id, 0.0) + sim * rating
            sum_sims[book_id] = sum_sims.get(book_id, 0.0) + sim

    normalized_scores: dict[str, float] = {}
    for book_id, total_weighted_rating in candidate_scores.items():
        if sum_sims[book_id] > 0:
            raw_score = total_weighted_rating / sum_sims[book_id]
            normalized_scores[book_id] = round(min(5.0, max(0.0, raw_score)), 3)

    return normalized_scores


def recommend_cold_start(
    limit: int = 10,
    books_df: pd.DataFrame | None = None,
    excluded_book_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Tier 1 Cold Start for Guests: High-rated, featured, diverse books.
    """
    df = books_df if books_df is not None else get_books_df()
    if df.empty:
        return []

    excluded = excluded_book_ids or set()
    df_copy = df[~df["book_id"].astype(str).isin(excluded)].copy()
    if df_copy.empty:
        df_copy = df.copy()

    df_copy["rating_num"] = pd.to_numeric(df_copy["rating"], errors="coerce").fillna(4.0)
    df_copy["is_featured"] = df_copy["featured"].apply(lambda v: v is True or str(v).lower() in ("true", "1"))
    df_copy["year_num"] = pd.to_numeric(df_copy["year"], errors="coerce").fillna(0)

    sorted_df = df_copy.sort_values(
        by=["is_featured", "rating_num", "year_num"],
        ascending=[False, False, False],
    )

    results = []
    for _, row in sorted_df.iterrows():
        b_dict = row.to_dict()
        rating_val = round(float(b_dict.get("rating_num", 4.0)), 1)
        reason = f"Tác phẩm tiêu biểu được đánh giá cao ({rating_val}★) tại Thư viện số AI"
        results.append({
            **b_dict,
            "score": round(5.0 if b_dict.get("is_featured") else 4.0, 2),
            "reason": reason,
            "reason_type": "popular_featured",
            "user_feedback": None,
        })

    return _apply_diversity_filter(results, limit=limit)


def recommend_for_user(
    username: str | None,
    limit: int = 10,
    weights: RecommendationWeights = DEFAULT_WEIGHTS,
    books_df: pd.DataFrame | None = None,
    algorithm: str = "hybrid",
) -> tuple[list[dict[str, Any]], str, bool]:
    """
    Main Hybrid Recommendation Engine:
    Combines Bookshelf data, User Preferences, ChromaDB Semantic Similarity,
    Collaborative Filtering from Community interactions, and User Feedback.
    Returns (recommendations, source_basis, is_personalized).
    """
    df = books_df if books_df is not None else get_books_df()
    if df.empty:
        return [], "Không có dữ liệu sách trong thư viện", False

    # 1. Nếu là Guest hoặc không có username -> Dùng Cold Start
    if not username:
        cold = recommend_cold_start(limit=limit, books_df=df)
        return cold, "Các tác phẩm nổi bật được cộng đồng yêu thích nhất", False

    # 2. Tải dữ liệu cá nhân của user
    user_data = load_user_recommendation_data(username)
    preferences = user_data.get("preferences", {})
    feedback = user_data.get("feedback", {})

    pref_genres = {normalize_search_text(g) for g in preferences.get("preferred_genres", []) if normalize_search_text(g)}
    pref_authors = {normalize_search_text(a) for a in preferences.get("preferred_authors", []) if normalize_search_text(a)}

    # Tải tủ sách cá nhân
    shelf = _load_user_bookshelf(username)
    shelf_items = shelf.get("items", {})

    favorite_bids = {
        str(it.get("book_id") or bid).strip()
        for bid, it in shelf_items.items()
        if it.get("status") == "favorite" or "favorite" in it.get("statuses", [])
    }
    reading_bids = {
        str(it.get("book_id") or bid).strip()
        for bid, it in shelf_items.items()
        if it.get("status") == "reading" or "reading" in it.get("statuses", [])
    }
    completed_bids = {
        str(it.get("book_id") or bid).strip()
        for bid, it in shelf_items.items()
        if it.get("status") == "completed" or "completed" in it.get("statuses", [])
    }

    disliked_bids = {str(bid) for bid, f in feedback.items() if f.get("liked") is False}
    liked_bids = {str(bid) for bid, f in feedback.items() if f.get("liked") is True}

    has_shelf_history = bool(favorite_bids or reading_bids or completed_bids)
    has_pref_history = bool(pref_genres or pref_authors)

    # 3. User mới chưa có dữ liệu tủ sách và sở thích (Cold Start hoàn toàn)
    if not has_shelf_history and not has_pref_history and not liked_bids:
        cold = recommend_cold_start(limit=limit, books_df=df, excluded_book_ids=disliked_bids)
        for c in cold:
            c["user_feedback"] = "liked" if c["book_id"] in liked_bids else None
        basis = "Gợi ý được điều chỉnh theo phản hồi của bạn" if disliked_bids else "Gợi ý khởi đầu dành cho bạn - Hãy chọn thể loại yêu thích để cá nhân hóa tốt hơn"
        return cold, basis, bool(disliked_bids)

    # 4. Trích xuất đặc trưng của các cuốn sách tích cực
    positive_bids = favorite_bids | reading_bids | liked_bids
    if not positive_bids and completed_bids:
        positive_bids = completed_bids

    base_books_df = df[df["book_id"].astype(str).isin(positive_bids)]
    positive_genres = {str(g).strip().lower() for g in base_books_df["genre"].dropna()}
    positive_authors = {str(a).strip().lower() for a in base_books_df["author"].dropna()}
    positive_tags: set[str] = set()
    for t_str in base_books_df["tags"].dropna():
        positive_tags.update(_extract_tags_set(t_str))

    # Semantic similarity từ ChromaDB qua vector centroid
    semantic_scores: dict[str, float] = {}
    if positive_bids:
        semantic_scores = query_semantic_by_book_ids(list(positive_bids)[:5], n_results=30)

    # Collaborative Filtering scores
    cf_scores: dict[str, float] = {}
    if algorithm in ("hybrid", "collaborative"):
        try:
            user_matrix = build_user_interaction_matrix()
            excluded_for_cf = reading_bids | completed_bids | favorite_bids | disliked_bids
            cf_scores = compute_collaborative_filtering_scores(
                username=username,
                user_matrix=user_matrix,
                excluded_bids=excluded_for_cf,
            )
        except Exception as exc:
            LOGGER.warning("Collaborative filtering computation failed gracefully: %s", exc)

    # 5. Chấm điểm từng cuốn sách ứng viên
    candidates: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        b_dict = row.to_dict()
        b_id = str(b_dict.get("book_id", ""))

        # Loại trừ: Sách bị Dislike
        if b_id in disliked_bids:
            continue

        # Loại trừ: Sách người dùng đang đọc hoặc đã đọc
        if b_id in reading_bids or b_id in completed_bids or b_id in favorite_bids:
            continue

        score = 0.0
        reason_type = "hybrid"
        reasons_list: list[str] = []

        b_genre = str(b_dict.get("genre", "")).strip().lower()
        b_author = str(b_dict.get("author", "")).strip().lower()
        b_tags = _extract_tags_set(b_dict.get("tags", ""))
        b_rating = float(pd.to_numeric(b_dict.get("rating"), errors="coerce") or 4.0)

        # Content Match: Trùng thể loại với sở thích đã chọn
        if normalize_search_text(b_genre) in pref_genres:
            score += weights.preferred_genre
            reasons_list.append(f"khớp sở thích thể loại '{b_dict.get('genre')}' của bạn")
            reason_type = "preferred_genre"

        # Content Match: Trùng tác giả với sở thích đã chọn
        if normalize_search_text(b_author) in pref_authors:
            score += weights.preferred_author
            reasons_list.append(f"tác giả '{b_dict.get('author')}' bạn quan tâm")

        # Bookshelf Match: Trùng thể loại với sách yêu thích/đang đọc
        if b_genre in positive_genres:
            score += weights.same_genre
            if not reasons_list:
                reasons_list.append(f"cùng thể loại '{b_dict.get('genre')}' với sách bạn quan tâm")
                reason_type = "bookshelf_favorite"

        # Bookshelf Match: Trùng tác giả
        if b_author in positive_authors:
            score += weights.same_author
            reasons_list.append(f"cùng tác giả '{b_dict.get('author')}'")

        # Tags Overlap
        common_tags = b_tags.intersection(positive_tags)
        if common_tags:
            score += min(len(common_tags) * 0.5, 3.0) * weights.tags_overlap

        # Semantic Similarity từ ChromaDB
        if b_id in semantic_scores:
            sem_val = semantic_scores[b_id]
            score += sem_val * weights.semantic_vector
            if sem_val > 0.75 and not reasons_list:
                reasons_list.append("nội dung và thông điệp tương đồng sâu sắc với gu đọc của bạn")
                reason_type = "semantic_similar"

        # Like Feedback Boost
        if b_id in liked_bids:
            score += weights.liked_feedback_boost
            reasons_list.append("bạn đã từng thích cuốn sách này")

        # Rating Bonus
        score += (b_rating - 3.5) * weights.rating_bonus

        # Collaborative Filtering Integration
        cf_val = cf_scores.get(b_id, 0.0)
        if algorithm == "collaborative":
            if cf_scores:
                score = cf_val if cf_val > 0 else 0.2 * score
                if cf_val > 0:
                    reasons_list.insert(0, f"được nhiều bạn đọc có gu tương tự đọc và đánh giá cao ({cf_val:.1f} điểm)")
                    reason_type = "collaborative_community"
        elif algorithm == "hybrid":
            if cf_val > 0:
                score = 0.6 * score + 0.4 * cf_val
                reasons_list.append("được bạn đọc có cùng gu đọc yêu thích")
                if reason_type == "popular_featured":
                    reason_type = "hybrid"

        # Xây dựng câu giải thích lý do
        if reasons_list:
            final_reason = f"Được đề xuất vì {reasons_list[0]}"
            if len(reasons_list) > 1:
                final_reason += f" và {reasons_list[1]}"
            final_reason += f" ({b_rating:.1f}★)."
        else:
            final_reason = f"Tác phẩm chất lượng cao ({b_rating:.1f}★) phù hợp để khám phá thêm."
            reason_type = "popular_featured"

        user_fb = "liked" if b_id in liked_bids else None

        candidates.append({
            **b_dict,
            "score": round(score, 3),
            "reason": final_reason,
            "reason_type": reason_type,
            "user_feedback": user_fb,
        })

    # 6. Sắp xếp điểm số và Áp dụng Đa dạng hóa
    candidates.sort(key=lambda x: x["score"], reverse=True)
    diversified = _apply_diversity_filter(
        candidates,
        limit=limit,
        max_per_genre_ratio=weights.max_per_genre_ratio,
        max_per_author_ratio=weights.max_per_author_ratio,
    )

    # 7. Mô tả nguồn cơ sở gợi ý
    basis_parts = []
    if pref_genres:
        basis_parts.append(f"sở thích thể loại ({', '.join(preferences.get('preferred_genres', [])[:2])})")
    if positive_bids:
        basis_parts.append("các sách trong tủ sách cá nhân của bạn")
    source_basis = f"Dựa trên {' và '.join(basis_parts)}" if basis_parts else "Dựa trên hồ sơ đọc sách của bạn"
    if algorithm == "collaborative":
        if cf_scores:
            source_basis = "Gợi ý theo thuật toán Lọc cộng tác (Collaborative Filtering) từ cộng đồng độc giả tương đồng"
        else:
            source_basis += " (Cơ chế Cold-Start: tự động bảo vệ khi tương tác cộng đồng đang tích lũy)"
    elif algorithm == "hybrid" and cf_scores:
        source_basis += " kết hợp hành vi cộng đồng độc giả tương đồng (Hybrid)"


    return diversified, source_basis, True


def recommend_continue_reading(
    username: str,
    limit: int = 6,
    weights: RecommendationWeights = DEFAULT_WEIGHTS,
    books_df: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """
    Recommend books specifically similar to books currently in 'reading' status.
    """
    df = books_df if books_df is not None else get_books_df()
    if df.empty:
        return []

    shelf = _load_user_bookshelf(username)
    shelf_items = shelf.get("items", {})
    reading_bids = [
        str(it.get("book_id") or bid).strip()
        for bid, it in shelf_items.items()
        if it.get("status") == "reading" or "reading" in it.get("statuses", [])
    ]

    if not reading_bids:
        favorite_bids = [
            str(it.get("book_id") or bid).strip()
            for bid, it in shelf_items.items()
            if it.get("status") == "favorite" or "favorite" in it.get("statuses", [])
        ]
        if favorite_bids:
            return recommend_similar_books(favorite_bids[0], limit=limit, weights=weights, books_df=df)
        return []

    active_book_id = reading_bids[0]
    base_book = get_book_by_id(active_book_id, df)
    if not base_book:
        return []

    similar = recommend_similar_books(active_book_id, limit=limit, weights=weights, books_df=df)
    for s in similar:
        s["reason"] = f"Phù hợp để tiếp tục mạch đọc khi bạn đang đọc cuốn '{base_book.get('title')}'"
        s["reason_type"] = "continue_reading"
    return similar


def recommend_similar_books(
    book_id: str,
    limit: int = 6,
    weights: RecommendationWeights = DEFAULT_WEIGHTS,
    books_df: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """
    Recommend books similar to a specific book using Content-Based + ChromaDB Semantic search.
    """
    df = books_df if books_df is not None else get_books_df()
    base_book = get_book_by_id(book_id, df)
    if not base_book:
        return []

    book_genre = str(base_book.get("genre", "")).strip().lower()
    book_author = str(base_book.get("author", "")).strip().lower()
    book_tags = _extract_tags_set(base_book.get("tags", ""))
    book_title = str(base_book.get("title", ""))

    # Vector similarity trực tiếp từ ChromaDB
    semantic_scores = query_semantic_by_book_ids([str(book_id)], n_results=limit * 3)

    candidates = []
    for _, row in df.iterrows():
        b_dict = row.to_dict()
        b_id = str(b_dict.get("book_id", ""))
        if b_id == str(book_id):
            continue

        score = 0.0
        reasons: list[str] = []

        if str(b_dict.get("genre", "")).strip().lower() == book_genre:
            score += weights.same_genre
            reasons.append(f"cùng thể loại {b_dict.get('genre')}")

        if str(b_dict.get("author", "")).strip().lower() == book_author:
            score += weights.same_author * 1.5
            reasons.append(f"cùng tác giả {b_dict.get('author')}")

        b_tags = _extract_tags_set(b_dict.get("tags", ""))
        common = book_tags.intersection(b_tags)
        if common:
            score += len(common) * weights.tags_overlap

        if b_id in semantic_scores:
            score += semantic_scores[b_id] * weights.semantic_vector

        b_rating = float(pd.to_numeric(b_dict.get("rating"), errors="coerce") or 4.0)
        score += (b_rating - 3.5) * weights.rating_bonus

        reason_str = f"Tương đồng với cuốn '{book_title}'"
        if reasons:
            reason_str += f" ({', '.join(reasons)})"

        candidates.append({
            **b_dict,
            "score": round(score, 3),
            "reason": reason_str,
            "reason_type": "similar_book",
            "user_feedback": None,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]
