"""
Social Community Service Module
Encapsulates business logic for User Profiles, Reviews, Threaded Comments,
and Reactions with strict security, IDOR prevention, and atomic counters.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, status

from backend.core.database import get_books_df, load_users
from backend.routers.bookshelf_router import _enrich_book_metadata, _load_user_bookshelf
from backend.services.community_db import get_db, run_migrations
from book_service import get_book_by_id

LOGGER = logging.getLogger(__name__)

# Ensure schema is up to date on module load
try:
    run_migrations()
except Exception as e:
    LOGGER.warning("Could not auto-run community database migrations on startup: %s", e)


def _get_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# User Profile Operations
# ==============================================================================

def get_or_create_profile(username: str, conn=None) -> dict[str, Any]:
    """Retrieve an existing user profile or initialize a default one."""
    cleaned_user = str(username).strip()
    if not cleaned_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tên người dùng không hợp lệ")

    def _execute(db_conn):
        cursor = db_conn.execute("SELECT * FROM user_profiles WHERE username = ?;", (cleaned_user,))
        row = cursor.fetchone()
        if row:
            return dict(row)

        now = _get_now_iso()
        db_conn.execute(
            """
            INSERT OR IGNORE INTO user_profiles (
                username, display_name, avatar_url, bio,
                bookshelf_privacy, activity_privacy,
                created_at, updated_at
            )
            VALUES (?, ?, '', '', 'public', 'public', ?, ?);
            """,
            (cleaned_user, cleaned_user, now, now),
        )
        cursor = db_conn.execute("SELECT * FROM user_profiles WHERE username = ?;", (cleaned_user,))
        new_row = cursor.fetchone()
        return dict(new_row) if new_row else {
            "username": cleaned_user,
            "display_name": cleaned_user,
            "avatar_url": "",
            "bio": "",
            "bookshelf_privacy": "public",
            "activity_privacy": "public",
            "created_at": now,
            "updated_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db() as db_conn:
        return _execute(db_conn)


def get_user_profile(username: str) -> dict[str, Any]:
    """Get public profile with aggregated statistics."""
    cleaned_user = str(username).strip()
    with get_db() as conn:
        profile = get_or_create_profile(cleaned_user, conn=conn)

        # Count active reviews
        c_cur = conn.execute(
            "SELECT COUNT(*) AS rev_cnt FROM reviews WHERE username = ? AND status = 'active';",
            (cleaned_user,),
        )
        rev_count = c_cur.fetchone()["rev_cnt"]
        profile["reviews_count"] = rev_count

        # Count followers
        fol_cur = conn.execute(
            "SELECT COUNT(*) AS f_cnt FROM follows WHERE following_username = ?;",
            (cleaned_user,),
        )
        profile["followers_count"] = fol_cur.fetchone()["f_cnt"]

        # Count following
        fing_cur = conn.execute(
            "SELECT COUNT(*) AS fing_cnt FROM follows WHERE follower_username = ?;",
            (cleaned_user,),
        )
        profile["following_count"] = fing_cur.fetchone()["fing_cnt"]

        if not profile.get("bookshelf_privacy"):
            profile["bookshelf_privacy"] = "public"
        if not profile.get("activity_privacy"):
            profile["activity_privacy"] = "public"

        return profile


def update_user_profile(
    username: str,
    display_name: str,
    avatar_url: str = "",
    bio: str = "",
) -> dict[str, Any]:
    """Update profile details of the authenticated user."""
    cleaned_user = str(username).strip()
    cleaned_name = str(display_name).strip()
    if not cleaned_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tên hiển thị không được để trống")

    now = _get_now_iso()
    with get_db() as conn:
        # Ensure row exists
        get_or_create_profile(cleaned_user, conn=conn)

        conn.execute(
            """
            UPDATE user_profiles
            SET display_name = ?, avatar_url = ?, bio = ?, updated_at = ?
            WHERE username = ?;
            """,
            (cleaned_name, str(avatar_url).strip(), str(bio).strip(), now, cleaned_user),
        )

    return get_user_profile(cleaned_user)


# ==============================================================================
# Review Operations
# ==============================================================================

def create_review(
    username: str,
    book_id: str,
    rating: int,
    title: str,
    content: str,
    contains_spoiler: bool = False,
) -> dict[str, Any]:
    """Create a new book review. Enforces 1 review per user per book."""
    cleaned_user = str(username).strip()
    cleaned_book_id = str(book_id).strip()

    # 1. Validate book existence in books.csv
    books_df = get_books_df()
    book_rec = get_book_by_id(cleaned_book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sách với mã '{cleaned_book_id}' trong thư viện",
        )

    # 2. Validate input lengths
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số sao đánh giá phải từ 1 đến 5")
    clean_title = str(title).strip()
    clean_content = str(content).strip()
    if len(clean_title) < 3 or len(clean_title) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tiêu đề nhận xét phải từ 3 đến 200 ký tự")
    if len(clean_content) < 10 or len(clean_content) > 5000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nội dung nhận xét phải từ 10 đến 5000 ký tự")

    with get_db() as conn:
        # Ensure profile exists
        profile = get_or_create_profile(cleaned_user, conn=conn)

        # Check duplicate review
        check_cur = conn.execute(
            "SELECT id FROM reviews WHERE book_id = ? AND username = ?;",
            (cleaned_book_id, cleaned_user),
        )
        if check_cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn đã đánh giá cuốn sách này rồi. Vui lòng cập nhật bài đánh giá hiện có.",
            )

        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        now = _get_now_iso()

        conn.execute(
            """
            INSERT INTO reviews (
                id, book_id, username, rating, title, content,
                contains_spoiler, likes_count, comments_count, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'active', ?, ?);
            """,
            (
                review_id,
                cleaned_book_id,
                cleaned_user,
                rating,
                clean_title,
                clean_content,
                1 if contains_spoiler else 0,
                now,
                now,
            ),
        )

        # Record activity
        record_activity(
            username=cleaned_user,
            activity_type="review_created",
            entity_id=review_id,
            entity_type="review",
            metadata={
                "book_id": cleaned_book_id,
                "book_title": book_rec.get("title", ""),
                "rating": rating,
                "review_title": clean_title,
            },
            conn=conn,
        )

        return {
            "id": review_id,
            "book_id": cleaned_book_id,
            "username": cleaned_user,
            "user_display_name": profile["display_name"],
            "user_avatar_url": profile["avatar_url"],
            "rating": rating,
            "title": clean_title,
            "content": clean_content,
            "contains_spoiler": bool(contains_spoiler),
            "likes_count": 0,
            "comments_count": 0,
            "user_liked": False,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }


def get_book_reviews(
    book_id: str,
    current_username: str | None = None,
    rating_filter: int | None = None,
    sort_by: str = "newest",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Retrieve reviews for a book with pagination, rating breakdown, and sort options."""
    cleaned_book_id = str(book_id).strip()
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size

    with get_db() as conn:
        # 1. Total and breakdown
        base_query = "SELECT rating, COUNT(*) AS cnt FROM reviews WHERE book_id = ? AND status = 'active'"
        breakdown_cur = conn.execute(f"{base_query} GROUP BY rating;", (cleaned_book_id,))
        breakdown = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        total_reviews = 0
        sum_rating = 0
        for row in breakdown_cur.fetchall():
            r_str = str(row["rating"])
            cnt = int(row["cnt"])
            breakdown[r_str] = cnt
            total_reviews += cnt
            sum_rating += int(row["rating"]) * cnt

        avg_rating = round(sum_rating / total_reviews, 1) if total_reviews > 0 else 0.0

        # 2. Main query with filter & sort
        where_clauses = ["r.book_id = ?", "r.status = 'active'"]
        params: list[Any] = [cleaned_book_id]

        if rating_filter is not None and 1 <= rating_filter <= 5:
            where_clauses.append("r.rating = ?")
            params.append(rating_filter)

        sort_sql = "r.created_at DESC"
        if sort_by == "popular":
            sort_sql = "r.likes_count DESC, r.created_at DESC"
        elif sort_by == "highest_rating":
            sort_sql = "r.rating DESC, r.created_at DESC"
        elif sort_by == "lowest_rating":
            sort_sql = "r.rating ASC, r.created_at DESC"

        where_stmt = " AND ".join(where_clauses)

        # Count filtered
        count_cur = conn.execute(f"SELECT COUNT(*) AS filtered_cnt FROM reviews r WHERE {where_stmt};", params)
        filtered_count = count_cur.fetchone()["filtered_cnt"]

        # Fetch records
        query_sql = f"""
            SELECT 
                r.*,
                p.display_name AS user_display_name,
                p.avatar_url AS user_avatar_url,
                (
                    SELECT 1 FROM reactions rx 
                    WHERE rx.target_type = 'review' 
                      AND rx.target_id = r.id 
                      AND rx.username = ?
                ) AS has_liked
            FROM reviews r
            LEFT JOIN user_profiles p ON r.username = p.username
            WHERE {where_stmt}
            ORDER BY {sort_sql}
            LIMIT ? OFFSET ?;
        """
        fetch_params = [current_username or ""] + params + [page_size, offset]
        rows = conn.execute(query_sql, fetch_params).fetchall()

        reviews_list = []
        for r in rows:
            reviews_list.append({
                "id": r["id"],
                "book_id": r["book_id"],
                "username": r["username"],
                "user_display_name": r["user_display_name"] or r["username"],
                "user_avatar_url": r["user_avatar_url"] or "",
                "rating": r["rating"],
                "title": r["title"],
                "content": r["content"],
                "contains_spoiler": bool(r["contains_spoiler"]),
                "likes_count": r["likes_count"],
                "comments_count": r["comments_count"],
                "user_liked": bool(r["has_liked"]),
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })

        return {
            "total": filtered_count,
            "page": page,
            "page_size": page_size,
            "average_rating": avg_rating,
            "rating_breakdown": breakdown,
            "reviews": reviews_list,
        }


def get_review_detail(
    review_id: str,
    current_username: str | None = None,
    is_admin: bool = False,
) -> dict[str, Any]:
    """Get single review detail by review_id."""
    clean_id = str(review_id).strip()
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT 
                r.*,
                p.display_name AS user_display_name,
                p.avatar_url AS user_avatar_url,
                (
                    SELECT 1 FROM reactions rx 
                    WHERE rx.target_type = 'review' 
                      AND rx.target_id = r.id 
                      AND rx.username = ?
                ) AS has_liked
            FROM reviews r
            LEFT JOIN user_profiles p ON r.username = p.username
            WHERE r.id = ? AND r.status != 'deleted';
            """,
            (current_username or "", clean_id),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài đánh giá")

        if row["status"] == "hidden" and not is_admin and (not current_username or current_username != row["username"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung đã bị ẩn do vi phạm tiêu chuẩn cộng đồng")

        return {
            "id": row["id"],
            "book_id": row["book_id"],
            "username": row["username"],
            "user_display_name": row["user_display_name"] or row["username"],
            "user_avatar_url": row["user_avatar_url"] or "",
            "rating": row["rating"],
            "title": row["title"],
            "content": row["content"],
            "contains_spoiler": bool(row["contains_spoiler"]),
            "likes_count": row["likes_count"],
            "comments_count": row["comments_count"],
            "user_liked": bool(row["has_liked"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def update_review(
    review_id: str,
    username: str,
    rating: int | None = None,
    title: str | None = None,
    content: str | None = None,
    contains_spoiler: bool | None = None,
) -> dict[str, Any]:
    """Update a review owned by username. IDOR protected."""
    clean_id = str(review_id).strip()
    clean_user = str(username).strip()

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM reviews WHERE id = ?;", (clean_id,))
        row = cursor.fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài đánh giá")

        if row["username"] != clean_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền chỉnh sửa bài đánh giá của người khác",
            )

        new_rating = rating if rating is not None else row["rating"]
        new_title = str(title).strip() if title is not None else row["title"]
        new_content = str(content).strip() if content is not None else row["content"]
        new_spoiler = 1 if (contains_spoiler if contains_spoiler is not None else bool(row["contains_spoiler"])) else 0

        if new_rating < 1 or new_rating > 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số sao phải từ 1 đến 5")
        if len(new_title) < 3 or len(new_title) > 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tiêu đề phải từ 3 đến 200 ký tự")
        if len(new_content) < 10 or len(new_content) > 5000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nội dung phải từ 10 đến 5000 ký tự")

        now = _get_now_iso()
        conn.execute(
            """
            UPDATE reviews
            SET rating = ?, title = ?, content = ?, contains_spoiler = ?, updated_at = ?
            WHERE id = ?;
            """,
            (new_rating, new_title, new_content, new_spoiler, now, clean_id),
        )

    return get_review_detail(clean_id, current_username=clean_user)


def delete_review(review_id: str, username: str, is_admin: bool = False) -> bool:
    """Delete review. Allowed for author or Admin."""
    clean_id = str(review_id).strip()
    clean_user = str(username).strip()

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM reviews WHERE id = ?;", (clean_id,))
        row = cursor.fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài đánh giá")

        if row["username"] != clean_user and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa bài đánh giá này",
            )

        # Hard delete triggers cascade delete on comments and reactions
        conn.execute("DELETE FROM reviews WHERE id = ?;", (clean_id,))
        conn.execute("DELETE FROM activity_feed WHERE activity_type = 'review_created' AND entity_id = ?;", (clean_id,))
        return True


# ==============================================================================
# Comment Operations
# ==============================================================================

def create_comment(
    username: str,
    review_id: str,
    content: str,
    parent_comment_id: str | None = None,
) -> dict[str, Any]:
    """Create a comment or threaded reply under a review."""
    clean_user = str(username).strip()
    clean_review_id = str(review_id).strip()
    clean_content = str(content).strip()
    clean_parent = str(parent_comment_id).strip() if parent_comment_id else None

    if len(clean_content) < 1 or len(clean_content) > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nội dung bình luận phải từ 1 đến 1000 ký tự")

    with get_db() as conn:
        profile = get_or_create_profile(clean_user, conn=conn)

        # 1. Verify parent review
        rev_cur = conn.execute("SELECT id, status FROM reviews WHERE id = ?;", (clean_review_id,))
        rev_row = rev_cur.fetchone()
        if not rev_row or rev_row["status"] != "active":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bài đánh giá không tồn tại hoặc đã bị ẩn")

        # 2. Verify parent comment if reply
        if clean_parent:
            par_cur = conn.execute("SELECT id, review_id, status FROM comments WHERE id = ?;", (clean_parent,))
            par_row = par_cur.fetchone()
            if not par_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bình luận cha không tồn tại")
            if par_row["review_id"] != clean_review_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bình luận cha không thuộc bài đánh giá này")
            if par_row["status"] != "active":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không thể trả lời bình luận đã bị xóa hoặc ẩn")

        comment_id = f"cmt_{uuid.uuid4().hex[:12]}"
        now = _get_now_iso()

        conn.execute(
            """
            INSERT INTO comments (
                id, review_id, username, parent_comment_id, content,
                likes_count, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, 'active', ?, ?);
            """,
            (comment_id, clean_review_id, clean_user, clean_parent, clean_content, now, now),
        )

        # Atomic increment on review comments_count
        conn.execute(
            "UPDATE reviews SET comments_count = comments_count + 1 WHERE id = ?;",
            (clean_review_id,),
        )

        return {
            "id": comment_id,
            "review_id": clean_review_id,
            "username": clean_user,
            "user_display_name": profile["display_name"],
            "user_avatar_url": profile["avatar_url"],
            "parent_comment_id": clean_parent,
            "content": clean_content,
            "likes_count": 0,
            "user_liked": False,
            "replies_count": 0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }


def get_review_comments(
    review_id: str,
    current_username: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Retrieve comments for a review with pagination and reply counts."""
    clean_review_id = str(review_id).strip()
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    with get_db() as conn:
        count_cur = conn.execute(
            "SELECT COUNT(*) AS total FROM comments WHERE review_id = ? AND status = 'active';",
            (clean_review_id,),
        )
        total = count_cur.fetchone()["total"]

        query_sql = """
            SELECT 
                c.*,
                p.display_name AS user_display_name,
                p.avatar_url AS user_avatar_url,
                (
                    SELECT COUNT(*) FROM comments rpl 
                    WHERE rpl.parent_comment_id = c.id AND rpl.status = 'active'
                ) AS replies_count,
                (
                    SELECT 1 FROM reactions rx 
                    WHERE rx.target_type = 'comment' 
                      AND rx.target_id = c.id 
                      AND rx.username = ?
                ) AS has_liked
            FROM comments c
            LEFT JOIN user_profiles p ON c.username = p.username
            WHERE c.review_id = ? AND c.status = 'active'
            ORDER BY c.created_at ASC
            LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query_sql, (current_username or "", clean_review_id, page_size, offset)).fetchall()

        comments_list = []
        for r in rows:
            comments_list.append({
                "id": r["id"],
                "review_id": r["review_id"],
                "username": r["username"],
                "user_display_name": r["user_display_name"] or r["username"],
                "user_avatar_url": r["user_avatar_url"] or "",
                "parent_comment_id": r["parent_comment_id"],
                "content": r["content"],
                "likes_count": r["likes_count"],
                "user_liked": bool(r["has_liked"]),
                "replies_count": r["replies_count"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "comments": comments_list,
        }


def update_comment(comment_id: str, username: str, content: str) -> dict[str, Any]:
    """Update a comment. Protected: only the author can update."""
    clean_id = str(comment_id).strip()
    clean_user = str(username).strip()
    clean_content = str(content).strip()

    if len(clean_content) < 1 or len(clean_content) > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nội dung phải từ 1 đến 1000 ký tự")

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM comments WHERE id = ?;", (clean_id,))
        row = cursor.fetchone()
        if not row or row["status"] != "active":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bình luận")

        if row["username"] != clean_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền sửa bình luận này")

        now = _get_now_iso()
        conn.execute("UPDATE comments SET content = ?, updated_at = ? WHERE id = ?;", (clean_content, now, clean_id))

        profile = get_or_create_profile(clean_user, conn=conn)
        return {
            "id": row["id"],
            "review_id": row["review_id"],
            "username": clean_user,
            "user_display_name": profile["display_name"],
            "user_avatar_url": profile["avatar_url"],
            "parent_comment_id": row["parent_comment_id"],
            "content": clean_content,
            "likes_count": row["likes_count"],
            "user_liked": False,
            "status": "active",
            "created_at": row["created_at"],
            "updated_at": now,
        }


def delete_comment(comment_id: str, username: str, is_admin: bool = False) -> bool:
    """Delete a comment. Author or Admin permitted."""
    clean_id = str(comment_id).strip()
    clean_user = str(username).strip()

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM comments WHERE id = ?;", (clean_id,))
        row = cursor.fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bình luận")

        if row["username"] != clean_user and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xóa bình luận này")

        review_id = row["review_id"]
        conn.execute("DELETE FROM comments WHERE id = ?;", (clean_id,))

        # Decrement review comments_count
        conn.execute(
            "UPDATE reviews SET comments_count = MAX(0, comments_count - 1) WHERE id = ?;",
            (review_id,),
        )
        return True


# ==============================================================================
# Reaction Operations (Like / Unlike)
# ==============================================================================

def toggle_reaction(
    username: str,
    target_type: str,
    target_id: str,
    is_like: bool,
) -> dict[str, Any]:
    """
    Like or Unlike a review or comment.
    Enforces:
    1. Target must exist.
    2. Cannot like your own content (Self-like blocked).
    3. Duplicate like rejected.
    4. Unlike when not liked rejected.
    5. Atomic increment / decrement of likes_count.
    """
    clean_user = str(username).strip()
    clean_type = str(target_type).strip().lower()
    clean_id = str(target_id).strip()

    if clean_type not in ("review", "comment"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loại mục tiêu không hợp lệ")

    with get_db() as conn:
        # Ensure user profile
        get_or_create_profile(clean_user, conn=conn)

        # 1. Verify target existence and fetch owner
        table = "reviews" if clean_type == "review" else "comments"
        cur = conn.execute(f"SELECT username, likes_count, status FROM {table} WHERE id = ?;", (clean_id,))
        target_row = cur.fetchone()
        if not target_row or target_row["status"] != "active":
            name_vi = "Bài đánh giá" if clean_type == "review" else "Bình luận"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name_vi} không tồn tại hoặc đã bị ẩn")

        # 2. Block self-like
        if is_like and target_row["username"] == clean_user:
            name_vi = "bài đánh giá" if clean_type == "review" else "bình luận"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bạn không thể tự thích {name_vi} của chính mình",
            )

        # 3. Check existing reaction
        check_cur = conn.execute(
            "SELECT id FROM reactions WHERE username = ? AND target_type = ? AND target_id = ?;",
            (clean_user, clean_type, clean_id),
        )
        existing = check_cur.fetchone()

        if is_like:
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bạn đã thích nội dung này trước đó",
                )
            rx_id = f"rx_{uuid.uuid4().hex[:12]}"
            now = _get_now_iso()
            conn.execute(
                "INSERT INTO reactions (id, username, target_type, target_id, created_at) VALUES (?, ?, ?, ?, ?);",
                (rx_id, clean_user, clean_type, clean_id, now),
            )
            conn.execute(f"UPDATE {table} SET likes_count = likes_count + 1 WHERE id = ?;", (clean_id,))
        else:
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bạn chưa thích nội dung này",
                )
            conn.execute(
                "DELETE FROM reactions WHERE username = ? AND target_type = ? AND target_id = ?;",
                (clean_user, clean_type, clean_id),
            )
            conn.execute(f"UPDATE {table} SET likes_count = MAX(0, likes_count - 1) WHERE id = ?;", (clean_id,))

        # Query updated likes_count
        updated_cur = conn.execute(f"SELECT likes_count FROM {table} WHERE id = ?;", (clean_id,))
        new_count = updated_cur.fetchone()["likes_count"]

        return {
            "success": True,
            "target_type": clean_type,
            "target_id": clean_id,
            "liked": is_like,
            "likes_count": new_count,
            "message": "Đã thích thành công" if is_like else "Đã bỏ thích thành công",
        }


# ==============================================================================
# Phase 3.4.2: Follow, Friendship, Activity Feed, and Public Bookshelf Services
# ==============================================================================

def check_user_exists(username: str, conn=None) -> bool:
    """Check if a user exists in auth users.json or community user_profiles."""
    cleaned = str(username).strip()
    if not cleaned:
        return False
    users = load_users()
    if cleaned in users:
        return True

    def _exec(db_conn):
        cur = db_conn.execute("SELECT 1 FROM user_profiles WHERE username = ?;", (cleaned,))
        return cur.fetchone() is not None

    if conn is not None:
        return _exec(conn)
    with get_db() as db_conn:
        return _exec(db_conn)


# ------------------------------------------------------------------------------
# Follow Operations
# ------------------------------------------------------------------------------

def follow_user(follower_username: str, target_username: str) -> dict[str, Any]:
    """Follow another user. One-way relationship."""
    follower = str(follower_username).strip()
    target = str(target_username).strip()

    if follower == target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bạn không thể tự theo dõi chính mình")

    if not check_user_exists(target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{target}'")

    with get_db() as conn:
        get_or_create_profile(follower, conn=conn)
        get_or_create_profile(target, conn=conn)

        cur = conn.execute(
            "SELECT 1 FROM follows WHERE follower_username = ? AND following_username = ?;",
            (follower, target),
        )
        if cur.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bạn đã theo dõi người dùng này rồi")

        now = _get_now_iso()
        conn.execute(
            "INSERT INTO follows (follower_username, following_username, created_at) VALUES (?, ?, ?);",
            (follower, target, now),
        )

    return {
        "success": True,
        "message": f"Đã theo dõi người dùng '{target}' thành công",
        "target_username": target,
        "is_following": True,
    }


def unfollow_user(follower_username: str, target_username: str) -> dict[str, Any]:
    """Unfollow a previously followed user."""
    follower = str(follower_username).strip()
    target = str(target_username).strip()

    if follower == target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thao tác không hợp lệ")

    with get_db() as conn:
        cur = conn.execute(
            "SELECT 1 FROM follows WHERE follower_username = ? AND following_username = ?;",
            (follower, target),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bạn chưa theo dõi người dùng này")

        conn.execute(
            "DELETE FROM follows WHERE follower_username = ? AND following_username = ?;",
            (follower, target),
        )

    return {
        "success": True,
        "message": f"Đã hủy theo dõi người dùng '{target}' thành công",
        "target_username": target,
        "is_following": False,
    }


def get_user_followers(username: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List followers of a user with pagination."""
    cleaned = str(username).strip()
    if not check_user_exists(cleaned):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{cleaned}'")

    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    with get_db() as conn:
        count_cur = conn.execute(
            "SELECT COUNT(*) AS total FROM follows WHERE following_username = ?;",
            (cleaned,),
        )
        total = count_cur.fetchone()["total"]

        cur = conn.execute(
            """
            SELECT f.follower_username AS username, f.created_at,
                   p.display_name, p.avatar_url, p.bio
            FROM follows f
            LEFT JOIN user_profiles p ON f.follower_username = p.username
            WHERE f.following_username = ?
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (cleaned, page_size, offset),
        )
        items = [
            {
                "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "avatar_url": row["avatar_url"] or "",
                "bio": row["bio"] or "",
                "created_at": row["created_at"],
            }
            for row in cur.fetchall()
        ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def get_user_following(username: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List users that a given user is following."""
    cleaned = str(username).strip()
    if not check_user_exists(cleaned):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{cleaned}'")

    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    with get_db() as conn:
        count_cur = conn.execute(
            "SELECT COUNT(*) AS total FROM follows WHERE follower_username = ?;",
            (cleaned,),
        )
        total = count_cur.fetchone()["total"]

        cur = conn.execute(
            """
            SELECT f.following_username AS username, f.created_at,
                   p.display_name, p.avatar_url, p.bio
            FROM follows f
            LEFT JOIN user_profiles p ON f.following_username = p.username
            WHERE f.follower_username = ?
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (cleaned, page_size, offset),
        )
        items = [
            {
                "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "avatar_url": row["avatar_url"] or "",
                "bio": row["bio"] or "",
                "created_at": row["created_at"],
            }
            for row in cur.fetchall()
        ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ------------------------------------------------------------------------------
# Two-Way Friendship Mechanism (for 'friends' Privacy Level)
# ------------------------------------------------------------------------------

def are_friends(user_a: str, user_b: str, conn=None) -> bool:
    """Check if two users have an established two-way friendship."""
    if not user_a or not user_b or user_a == user_b:
        return False
    u1, u2 = sorted([user_a, user_b])

    def _exec(db_conn):
        cur = db_conn.execute(
            "SELECT 1 FROM friendships WHERE user1_username = ? AND user2_username = ?;",
            (u1, u2),
        )
        return cur.fetchone() is not None

    if conn is not None:
        return _exec(conn)
    with get_db() as db_conn:
        return _exec(db_conn)


def send_friend_request(sender_username: str, receiver_username: str) -> dict[str, Any]:
    sender = str(sender_username).strip()
    receiver = str(receiver_username).strip()

    if sender == receiver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không thể gửi lời mời kết bạn cho chính mình")

    if not check_user_exists(receiver):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{receiver}'")

    if are_friends(sender, receiver):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hai bạn đã là bạn bè của nhau rồi")

    with get_db() as conn:
        get_or_create_profile(sender, conn=conn)
        get_or_create_profile(receiver, conn=conn)

        cur = conn.execute(
            "SELECT id, status FROM friend_requests WHERE sender_username = ? AND receiver_username = ?;",
            (sender, receiver),
        )
        existing = cur.fetchone()
        if existing and existing["status"] == "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bạn đã gửi lời mời kết bạn trước đó và đang chờ phản hồi")

        req_id = f"freq_{uuid.uuid4().hex[:12]}"
        now = _get_now_iso()

        if existing:
            conn.execute(
                "UPDATE friend_requests SET id = ?, status = 'pending', updated_at = ? WHERE sender_username = ? AND receiver_username = ?;",
                (req_id, now, sender, receiver),
            )
        else:
            conn.execute(
                """
                INSERT INTO friend_requests (id, sender_username, receiver_username, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?);
                """,
                (req_id, sender, receiver, now, now),
            )

    return {"success": True, "message": f"Đã gửi lời mời kết bạn tới '{receiver}'", "request_id": req_id}


def accept_friend_request(request_id: str, current_username: str) -> dict[str, Any]:
    clean_id = str(request_id).strip()
    clean_user = str(current_username).strip()

    with get_db() as conn:
        cur = conn.execute("SELECT * FROM friend_requests WHERE id = ?;", (clean_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lời mời kết bạn")

        if row["receiver_username"] != clean_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền chấp nhận lời mời này")

        if row["status"] != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lời mời kết bạn đã ở trạng thái {row['status']}")

        u1, u2 = sorted([row["sender_username"], row["receiver_username"]])
        now = _get_now_iso()

        conn.execute(
            """
            INSERT OR IGNORE INTO friendships (user1_username, user2_username, created_at)
            VALUES (?, ?, ?);
            """,
            (u1, u2, now),
        )
        conn.execute(
            "UPDATE friend_requests SET status = 'accepted', updated_at = ? WHERE id = ?;",
            (now, clean_id),
        )

    return {"success": True, "message": "Đã chấp nhận lời mời kết bạn thành công", "friend": row["sender_username"]}


def reject_friend_request(request_id: str, current_username: str) -> dict[str, Any]:
    clean_id = str(request_id).strip()
    clean_user = str(current_username).strip()

    with get_db() as conn:
        cur = conn.execute("SELECT * FROM friend_requests WHERE id = ?;", (clean_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lời mời kết bạn")

        if row["receiver_username"] != clean_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền từ chối lời mời này")

        now = _get_now_iso()
        conn.execute(
            "UPDATE friend_requests SET status = 'rejected', updated_at = ? WHERE id = ?;",
            (now, clean_id),
        )

    return {"success": True, "message": "Đã từ chối lời mời kết bạn"}


def get_pending_friend_requests(username: str) -> dict[str, Any]:
    cleaned = str(username).strip()
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT fr.id, fr.sender_username, fr.receiver_username, fr.status, fr.created_at,
                   p.display_name AS sender_display_name, p.avatar_url AS sender_avatar_url
            FROM friend_requests fr
            LEFT JOIN user_profiles p ON fr.sender_username = p.username
            WHERE fr.receiver_username = ? AND fr.status = 'pending'
            ORDER BY fr.created_at DESC;
            """,
            (cleaned,),
        )
        items = [
            {
                "id": row["id"],
                "sender_username": row["sender_username"],
                "sender_display_name": row["sender_display_name"] or row["sender_username"],
                "sender_avatar_url": row["sender_avatar_url"] or "",
                "receiver_username": row["receiver_username"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in cur.fetchall()
        ]

    return {"total": len(items), "items": items}


def get_user_friends(username: str) -> dict[str, Any]:
    cleaned = str(username).strip()
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT CASE WHEN user1_username = ? THEN user2_username ELSE user1_username END AS friend_username,
                   created_at
            FROM friendships
            WHERE user1_username = ? OR user2_username = ?
            ORDER BY created_at DESC;
            """,
            (cleaned, cleaned, cleaned),
        )
        friend_rows = cur.fetchall()
        items = []
        for r in friend_rows:
            f_user = r["friend_username"]
            p_cur = conn.execute("SELECT display_name, avatar_url, bio FROM user_profiles WHERE username = ?;", (f_user,))
            p_row = p_cur.fetchone()
            items.append({
                "username": f_user,
                "display_name": (p_row["display_name"] if p_row else f_user) or f_user,
                "avatar_url": (p_row["avatar_url"] if p_row else "") or "",
                "bio": (p_row["bio"] if p_row else "") or "",
                "created_at": r["created_at"],
            })

    return {"total": len(items), "items": items}


def remove_friend(user_a: str, user_b: str) -> dict[str, Any]:
    cleaned_a = str(user_a).strip()
    cleaned_b = str(user_b).strip()
    u1, u2 = sorted([cleaned_a, cleaned_b])

    with get_db() as conn:
        conn.execute("DELETE FROM friendships WHERE user1_username = ? AND user2_username = ?;", (u1, u2))

    return {"success": True, "message": "Đã hủy kết bạn thành công"}


# ------------------------------------------------------------------------------
# Privacy Settings
# ------------------------------------------------------------------------------

def update_privacy_settings(
    username: str,
    bookshelf_privacy: str | None = None,
    activity_privacy: str | None = None,
) -> dict[str, Any]:
    cleaned_user = str(username).strip()
    valid_levels = {"public", "friends", "private"}

    with get_db() as conn:
        profile = get_or_create_profile(cleaned_user, conn=conn)
        new_bs = bookshelf_privacy if bookshelf_privacy in valid_levels else profile.get("bookshelf_privacy", "public")
        new_act = activity_privacy if activity_privacy in valid_levels else profile.get("activity_privacy", "public")
        now = _get_now_iso()

        conn.execute(
            """
            UPDATE user_profiles
            SET bookshelf_privacy = ?, activity_privacy = ?, updated_at = ?
            WHERE username = ?;
            """,
            (new_bs, new_act, now, cleaned_user),
        )

    return {
        "username": cleaned_user,
        "bookshelf_privacy": new_bs,
        "activity_privacy": new_act,
        "updated_at": now,
    }


def get_privacy_settings(username: str) -> dict[str, Any]:
    cleaned_user = str(username).strip()
    with get_db() as conn:
        profile = get_or_create_profile(cleaned_user, conn=conn)
        return {
            "username": cleaned_user,
            "bookshelf_privacy": profile.get("bookshelf_privacy", "public"),
            "activity_privacy": profile.get("activity_privacy", "public"),
            "updated_at": profile.get("updated_at", _get_now_iso()),
        }


# ------------------------------------------------------------------------------
# Activity Feed Operations
# ------------------------------------------------------------------------------

def record_activity(
    username: str,
    activity_type: str,
    entity_id: str,
    entity_type: str,
    metadata: dict[str, Any] | None = None,
    conn=None,
) -> bool:
    """Record an authentic user activity without creating duplicates."""
    cleaned_user = str(username).strip()
    clean_type = str(activity_type).strip()
    clean_id = str(entity_id).strip()
    clean_ent_type = str(entity_type).strip()

    valid_types = {"review_created", "reading_started", "book_completed"}
    if clean_type not in valid_types or not cleaned_user or not clean_id:
        return False

    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    act_id = f"act_{uuid.uuid4().hex[:12]}"
    now = _get_now_iso()

    def _exec(db_conn):
        get_or_create_profile(cleaned_user, conn=db_conn)
        db_conn.execute(
            """
            INSERT OR IGNORE INTO activity_feed (
                id, username, activity_type, entity_id, entity_type, metadata_json, is_hidden, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?);
            """,
            (act_id, cleaned_user, clean_type, clean_id, clean_ent_type, meta_json, now),
        )
        return True

    if conn is not None:
        return _exec(conn)
    with get_db() as db_conn:
        return _exec(db_conn)


def get_feed(
    current_username: str,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Retrieve activity feed of accounts that current_user follows, applying privacy rules."""
    caller = str(current_username).strip()
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size

    with get_db() as conn:
        # 1. Get followed accounts
        fol_cur = conn.execute(
            "SELECT following_username FROM follows WHERE follower_username = ?;",
            (caller,),
        )
        following_users = [row["following_username"] for row in fol_cur.fetchall()]
        if not following_users:
            return {"total": 0, "page": page, "page_size": page_size, "items": []}

        # 2. Query activities from followed accounts
        placeholders = ",".join("?" for _ in following_users)
        query = f"""
            SELECT a.id, a.username, a.activity_type, a.entity_id, a.entity_type,
                   a.metadata_json, a.created_at,
                   p.display_name, p.avatar_url, p.activity_privacy, p.bookshelf_privacy,
                   r.status AS review_status
            FROM activity_feed a
            JOIN user_profiles p ON a.username = p.username
            LEFT JOIN reviews r ON (a.activity_type = 'review_created' AND a.entity_id = r.id)
            WHERE a.username IN ({placeholders})
              AND a.is_hidden = 0
            ORDER BY a.created_at DESC;
        """
        cur = conn.execute(query, following_users)
        all_candidate_rows = cur.fetchall()

        # 3. Apply privacy filters
        filtered_items = []
        for row in all_candidate_rows:
            author = row["username"]
            act_type = row["activity_type"]
            act_priv = row["activity_privacy"] or "public"
            shelf_priv = row["bookshelf_privacy"] or "public"

            # Check activity privacy
            if act_priv == "private":
                continue
            if act_priv == "friends" and not are_friends(caller, author, conn=conn):
                continue

            # Check bookshelf privacy for reading activities
            if act_type in {"reading_started", "book_completed"}:
                if shelf_priv == "private":
                    continue
                if shelf_priv == "friends" and not are_friends(caller, author, conn=conn):
                    continue

            # Check review status if review_created
            if act_type == "review_created" and row["review_status"] != "active":
                continue

            try:
                meta = json.loads(row["metadata_json"] or "{}")
            except Exception:
                meta = {}

            filtered_items.append({
                "id": row["id"],
                "username": author,
                "user_display_name": row["display_name"] or author,
                "user_avatar_url": row["avatar_url"] or "",
                "activity_type": act_type,
                "entity_id": row["entity_id"],
                "entity_type": row["entity_type"],
                "metadata": meta,
                "created_at": row["created_at"],
            })

        total = len(filtered_items)
        paginated_items = filtered_items[offset : offset + page_size]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": paginated_items,
        }


def get_user_activities(
    target_username: str,
    current_username: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Retrieve activities of a specific user with respect to privacy settings."""
    target = str(target_username).strip()
    caller = str(current_username).strip() if current_username else None

    if not check_user_exists(target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{target}'")

    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size

    with get_db() as conn:
        target_prof = get_or_create_profile(target, conn=conn)
        act_priv = target_prof.get("activity_privacy", "public")
        shelf_priv = target_prof.get("bookshelf_privacy", "public")

        is_owner = (caller == target)

        if not is_owner:
            if act_priv == "private":
                return {"total": 0, "page": page, "page_size": page_size, "items": []}
            if act_priv == "friends" and (not caller or not are_friends(caller, target, conn=conn)):
                return {"total": 0, "page": page, "page_size": page_size, "items": []}

        cur = conn.execute(
            """
            SELECT a.id, a.username, a.activity_type, a.entity_id, a.entity_type,
                   a.metadata_json, a.created_at,
                   r.status AS review_status
            FROM activity_feed a
            LEFT JOIN reviews r ON (a.activity_type = 'review_created' AND a.entity_id = r.id)
            WHERE a.username = ? AND a.is_hidden = 0
            ORDER BY a.created_at DESC;
            """,
            (target,),
        )
        all_rows = cur.fetchall()

        filtered = []
        for row in all_rows:
            act_type = row["activity_type"]

            if not is_owner:
                if act_type in {"reading_started", "book_completed"}:
                    if shelf_priv == "private":
                        continue
                    if shelf_priv == "friends" and (not caller or not are_friends(caller, target, conn=conn)):
                        continue

                if act_type == "review_created" and row["review_status"] != "active":
                    continue

            try:
                meta = json.loads(row["metadata_json"] or "{}")
            except Exception:
                meta = {}

            filtered.append({
                "id": row["id"],
                "username": target,
                "user_display_name": target_prof["display_name"],
                "user_avatar_url": target_prof["avatar_url"],
                "activity_type": act_type,
                "entity_id": row["entity_id"],
                "entity_type": row["entity_type"],
                "metadata": meta,
                "created_at": row["created_at"],
            })

        total = len(filtered)
        paginated = filtered[offset : offset + page_size]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": paginated,
        }


# ------------------------------------------------------------------------------
# Public Bookshelf Operations
# ------------------------------------------------------------------------------

def get_public_bookshelf(
    target_username: str,
    current_username: str | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    """Retrieve public bookshelf of a user strictly honoring privacy settings."""
    target = str(target_username).strip()
    caller = str(current_username).strip() if current_username else None

    if not check_user_exists(target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy người dùng '{target}'")

    with get_db() as conn:
        profile = get_or_create_profile(target, conn=conn)
        shelf_privacy = profile.get("bookshelf_privacy", "public")
        is_owner = (caller == target)

        if not is_owner:
            if shelf_privacy == "private":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tủ sách này được đặt ở chế độ riêng tư",
                )
            if shelf_privacy == "friends":
                if not caller or not are_friends(caller, target, conn=conn):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tủ sách này chỉ chia sẻ với bạn bè",
                    )

    # Load target user's bookshelf file
    shelf_data = _load_user_bookshelf(target)
    items_dict = shelf_data.get("items", {})

    result_items = []
    for item_id, item in items_dict.items():
        if status_filter and item.get("status") != status_filter:
            continue
        book_meta = _enrich_book_metadata(item.get("book_id", ""))
        result_items.append({
            "id": item.get("id", item_id),
            "book_id": item.get("book_id", ""),
            "title": book_meta.get("title", ""),
            "author": book_meta.get("author", ""),
            "cover_image": book_meta.get("cover_image", ""),
            "genre": book_meta.get("genre", ""),
            "publisher": book_meta.get("publisher", ""),
            "publish_year": book_meta.get("publish_year", 0),
            "rating": book_meta.get("rating", 0.0),
            "status": item.get("status", ""),
            "progress_page": item.get("progress_page", 0),
            "total_pages": item.get("total_pages", 0),
            "added_at": item.get("added_at", ""),
            "updated_at": item.get("updated_at", ""),
        })

    return {
        "username": target,
        "display_name": profile["display_name"],
        "bookshelf_privacy": shelf_privacy,
        "total": len(result_items),
        "items": result_items,
    }


# ==============================================================================
# Phase 3.4.3: Social Moderation & Reporting Services
# ==============================================================================

VALID_REPORT_REASONS = {"spam", "harassment", "misinformation", "inappropriate", "copyright", "other"}
VALID_REPORT_STATUSES = {"pending", "reviewing", "resolved", "dismissed"}
VALID_MODERATION_ACTIONS = {"warn", "hide", "restore", "delete"}


def create_report(
    reporter_username: str,
    target_type: str,
    target_id: str,
    reason: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new moderation report for a review or comment."""
    reporter = str(reporter_username).strip()
    clean_type = str(target_type).strip().lower()
    clean_id = str(target_id).strip()
    clean_reason = str(reason).strip().lower()
    clean_desc = str(description).strip()[:500]

    if clean_type not in {"review", "comment"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loại đối tượng phải là 'review' hoặc 'comment'")

    if clean_reason not in VALID_REPORT_REASONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lý do báo cáo không hợp lệ. Phải là một trong: {', '.join(VALID_REPORT_REASONS)}")

    with get_db() as conn:
        get_or_create_profile(reporter, conn=conn)

        # 1. Check target existence and get author
        if clean_type == "review":
            cur = conn.execute("SELECT username, status FROM reviews WHERE id = ?;", (clean_id,))
            target_row = cur.fetchone()
            if not target_row or target_row["status"] == "deleted":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài đánh giá được báo cáo")
            target_author = target_row["username"]
        else:
            cur = conn.execute("SELECT username, status FROM comments WHERE id = ?;", (clean_id,))
            target_row = cur.fetchone()
            if not target_row or target_row["status"] == "deleted":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bình luận được báo cáo")
            target_author = target_row["username"]

        # 2. Block self-reporting
        if target_author == reporter:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bạn không thể tự báo cáo nội dung của chính mình")

        # 3. Prevent duplicate pending/reviewing reports by the same user on the same content
        dup_cur = conn.execute(
            """
            SELECT id FROM reports
            WHERE reporter_username = ? AND target_type = ? AND target_id = ?
              AND status IN ('pending', 'reviewing');
            """,
            (reporter, clean_type, clean_id),
        )
        if dup_cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bạn đã gửi báo cáo cho nội dung này và báo cáo đang được xem xét",
            )

        rep_id = f"rep_{uuid.uuid4().hex[:12]}"
        now = _get_now_iso()

        conn.execute(
            """
            INSERT INTO reports (
                id, reporter_username, target_type, target_id, reason,
                description, status, claimed_by, claimed_at,
                resolved_by, resolved_at, admin_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, NULL, NULL, '', ?, ?);
            """,
            (rep_id, reporter, clean_type, clean_id, clean_reason, clean_desc, now, now),
        )

        return {
            "id": rep_id,
            "reporter_username": reporter,
            "target_type": clean_type,
            "target_id": clean_id,
            "reason": clean_reason,
            "description": clean_desc,
            "status": "pending",
            "claimed_by": None,
            "claimed_at": None,
            "resolved_by": None,
            "resolved_at": None,
            "admin_notes": "",
            "created_at": now,
            "updated_at": now,
        }


def get_my_reports(
    reporter_username: str,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List reports created by the current user."""
    reporter = str(reporter_username).strip()
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    where_clauses = ["reporter_username = ?"]
    params: list[Any] = [reporter]

    if status_filter and status_filter in VALID_REPORT_STATUSES:
        where_clauses.append("status = ?")
        params.append(status_filter)

    where_sql = " AND ".join(where_clauses)

    with get_db() as conn:
        count_cur = conn.execute(f"SELECT COUNT(*) AS total FROM reports WHERE {where_sql};", params)
        total = count_cur.fetchone()["total"]

        query_sql = f"""
            SELECT * FROM reports
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()
        items = [dict(r) for r in rows]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def get_admin_reports(
    status_filter: str | None = None,
    target_type_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Admin: list all reports with filtering, pagination, and status breakdown."""
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    with get_db() as conn:
        # Status counts breakdown
        counts_cur = conn.execute("SELECT status, COUNT(*) AS cnt FROM reports GROUP BY status;")
        status_counts = {"pending": 0, "reviewing": 0, "resolved": 0, "dismissed": 0}
        for r in counts_cur.fetchall():
            if r["status"] in status_counts:
                status_counts[r["status"]] = r["cnt"]

        where_clauses = []
        params: list[Any] = []

        if status_filter and status_filter in VALID_REPORT_STATUSES:
            where_clauses.append("status = ?")
            params.append(status_filter)

        if target_type_filter and target_type_filter in {"review", "comment"}:
            where_clauses.append("target_type = ?")
            params.append(target_type_filter)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_cur = conn.execute(f"SELECT COUNT(*) AS total FROM reports {where_sql};", params)
        total = count_cur.fetchone()["total"]

        query_sql = f"""
            SELECT * FROM reports
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()
        items = [dict(r) for r in rows]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "status_counts": status_counts,
        "items": items,
    }


def get_admin_report_detail(report_id: str) -> dict[str, Any]:
    """Admin: view full detail of a report, target content, and action history."""
    clean_id = str(report_id).strip()
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_id,))
        rep_row = cur.fetchone()
        if not rep_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo cáo")

        # Get reporter display name
        rep_user = rep_row["reporter_username"]
        p_cur = conn.execute("SELECT display_name FROM user_profiles WHERE username = ?;", (rep_user,))
        p_row = p_cur.fetchone()
        reporter_display_name = p_row["display_name"] if p_row else rep_user

        # Get target content detail
        target_type = rep_row["target_type"]
        target_id = rep_row["target_id"]
        target_content = ""
        target_author = ""
        target_status = "deleted"

        if target_type == "review":
            r_cur = conn.execute("SELECT title, content, username, status FROM reviews WHERE id = ?;", (target_id,))
            r_row = r_cur.fetchone()
            if r_row:
                target_content = f"[{r_row['title']}] {r_row['content']}"
                target_author = r_row["username"]
                target_status = r_row["status"]
        else:
            c_cur = conn.execute("SELECT content, username, status FROM comments WHERE id = ?;", (target_id,))
            c_row = c_cur.fetchone()
            if c_row:
                target_content = c_row["content"]
                target_author = c_row["username"]
                target_status = c_row["status"]

        # Get moderation action history
        h_cur = conn.execute(
            """
            SELECT * FROM moderation_actions
            WHERE report_id = ? OR (target_type = ? AND target_id = ?)
            ORDER BY created_at DESC;
            """,
            (clean_id, target_type, target_id),
        )
        history = [dict(h) for h in h_cur.fetchall()]

        res = dict(rep_row)
        res["reporter_display_name"] = reporter_display_name
        res["target_content"] = target_content
        res["target_author_username"] = target_author
        res["target_status"] = target_status
        res["history"] = history
        return res


def claim_report(report_id: str, admin_username: str) -> dict[str, Any]:
    """Admin: claim a pending report for review."""
    clean_id = str(report_id).strip()
    admin = str(admin_username).strip()

    with get_db() as conn:
        get_or_create_profile(admin, conn=conn)
        cur = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo cáo")

        current_status = row["status"]
        if current_status == "reviewing":
            if row["claimed_by"] and row["claimed_by"] != admin:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Báo cáo này đã được tiếp nhận bởi admin '{row['claimed_by']}'",
                )
            return dict(row)

        if current_status in {"resolved", "dismissed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Báo cáo đã ở trạng thái '{current_status}', không thể tiếp nhận lại",
            )

        now = _get_now_iso()
        conn.execute(
            """
            UPDATE reports
            SET status = 'reviewing', claimed_by = ?, claimed_at = ?, updated_at = ?
            WHERE id = ?;
            """,
            (admin, now, now, clean_id),
        )

        cur_updated = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_id,))
        return dict(cur_updated.fetchone())


def dismiss_report(report_id: str, admin_username: str, notes: str) -> dict[str, Any]:
    """Admin: dismiss an invalid report with required notes."""
    clean_id = str(report_id).strip()
    admin = str(admin_username).strip()
    clean_notes = str(notes).strip()

    if len(clean_notes) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ghi chú bác bỏ phải từ 3 ký tự trở lên")

    with get_db() as conn:
        get_or_create_profile(admin, conn=conn)
        cur = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo cáo")

        prev_status = row["status"]
        if prev_status in {"resolved", "dismissed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Báo cáo đã ở trạng thái '{prev_status}' trước đó",
            )

        now = _get_now_iso()
        # 1. Update report
        conn.execute(
            """
            UPDATE reports
            SET status = 'dismissed', resolved_by = ?, resolved_at = ?,
                admin_notes = ?, updated_at = ?
            WHERE id = ?;
            """,
            (admin, now, clean_notes, now, clean_id),
        )

        # 2. Record moderation action log
        act_id = f"mod_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO moderation_actions (
                id, admin_username, target_type, target_id, report_id,
                action, previous_status, new_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, 'dismiss', ?, 'dismissed', ?, ?);
            """,
            (act_id, admin, row["target_type"], row["target_id"], clean_id, prev_status, clean_notes, now),
        )

        cur_updated = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_id,))
        return dict(cur_updated.fetchone())


def execute_moderation_action(
    report_id: str,
    admin_username: str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    """
    Admin: take action against reported content (warn, hide, restore, delete).
    Executes in a single ACID transaction, updates content status, resolves reports,
    and logs the action.
    """
    clean_rep_id = str(report_id).strip()
    admin = str(admin_username).strip()
    clean_action = str(action).strip().lower()
    clean_reason = str(reason).strip()

    if clean_action not in VALID_MODERATION_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hành động kiểm duyệt không hợp lệ. Phải là một trong: {', '.join(VALID_MODERATION_ACTIONS)}",
        )

    if len(clean_reason) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lý do xử lý phải từ 3 ký tự trở lên")

    with get_db() as conn:
        get_or_create_profile(admin, conn=conn)
        # 1. Fetch report
        r_cur = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_rep_id,))
        rep_row = r_cur.fetchone()
        if not rep_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy báo cáo")

        target_type = rep_row["target_type"]
        target_id = rep_row["target_id"]

        # 2. Fetch target content and verify existence
        table = "reviews" if target_type == "review" else "comments"
        t_cur = conn.execute(f"SELECT status FROM {table} WHERE id = ?;", (target_id,))
        target_row = t_cur.fetchone()
        if not target_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung mục tiêu không tồn tại")

        prev_content_status = target_row["status"]
        now = _get_now_iso()

        # 3. Determine new content status & perform update
        if clean_action == "warn":
            new_content_status = prev_content_status
        elif clean_action == "hide":
            new_content_status = "hidden"
            conn.execute(f"UPDATE {table} SET status = 'hidden', updated_at = ? WHERE id = ?;", (now, target_id))
            if target_type == "review":
                conn.execute("UPDATE activity_feed SET is_hidden = 1 WHERE activity_type = 'review_created' AND entity_id = ?;", (target_id,))
        elif clean_action == "restore":
            new_content_status = "active"
            conn.execute(f"UPDATE {table} SET status = 'active', updated_at = ? WHERE id = ?;", (now, target_id))
            if target_type == "review":
                conn.execute("UPDATE activity_feed SET is_hidden = 0 WHERE activity_type = 'review_created' AND entity_id = ?;", (target_id,))
        elif clean_action == "delete":
            new_content_status = "deleted"
            conn.execute(f"UPDATE {table} SET status = 'deleted', updated_at = ? WHERE id = ?;", (now, target_id))
            if target_type == "review":
                conn.execute("DELETE FROM activity_feed WHERE activity_type = 'review_created' AND entity_id = ?;", (target_id,))

        # 4. Update the primary report -> 'resolved'
        conn.execute(
            """
            UPDATE reports
            SET status = 'resolved', resolved_by = ?, resolved_at = ?,
                admin_notes = ?, updated_at = ?
            WHERE id = ?;
            """,
            (admin, now, clean_reason, now, clean_rep_id),
        )

        # 5. Resolve all other pending/reviewing reports pointing to the exact same target
        other_note = f"Đã được xử lý cùng đợt kiểm duyệt: {clean_action}. {clean_reason}"
        conn.execute(
            """
            UPDATE reports
            SET status = 'resolved', resolved_by = ?, resolved_at = ?,
                admin_notes = ?, updated_at = ?
            WHERE target_type = ? AND target_id = ? AND status IN ('pending', 'reviewing') AND id != ?;
            """,
            (admin, now, other_note, now, target_type, target_id, clean_rep_id),
        )

        # 6. Record moderation_actions log
        act_id = f"mod_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO moderation_actions (
                id, admin_username, target_type, target_id, report_id,
                action, previous_status, new_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (act_id, admin, target_type, target_id, clean_rep_id, clean_action, prev_content_status, new_content_status, clean_reason, now),
        )

        # Return updated report and action record
        updated_rep_cur = conn.execute("SELECT * FROM reports WHERE id = ?;", (clean_rep_id,))
        updated_rep = dict(updated_rep_cur.fetchone())

        action_record = {
            "id": act_id,
            "admin_username": admin,
            "target_type": target_type,
            "target_id": target_id,
            "report_id": clean_rep_id,
            "action": clean_action,
            "previous_status": prev_content_status,
            "new_status": new_content_status,
            "reason": clean_reason,
            "created_at": now,
        }

        return {
            "success": True,
            "report": updated_rep,
            "action": action_record,
        }


def get_moderation_actions(
    target_type: str | None = None,
    target_id: str | None = None,
    admin_username: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Admin: retrieve paginated history of moderation actions."""
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    where_clauses = []
    params: list[Any] = []

    if target_type and target_type in {"review", "comment"}:
        where_clauses.append("target_type = ?")
        params.append(target_type)

    if target_id:
        where_clauses.append("target_id = ?")
        params.append(str(target_id).strip())

    if admin_username:
        where_clauses.append("admin_username = ?")
        params.append(str(admin_username).strip())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_db() as conn:
        count_cur = conn.execute(f"SELECT COUNT(*) AS total FROM moderation_actions {where_sql};", params)
        total = count_cur.fetchone()["total"]

        query_sql = f"""
            SELECT * FROM moderation_actions
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()
        items = [dict(r) for r in rows]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }



