from __future__ import annotations

import re
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, Query, status

from backend.core.security import get_current_user, get_current_user_optional
from backend.core.database import get_books_df
from backend.schemas.recommendation_schema import (
    UserPreferencesUpdate,
    UserPreferencesResponse,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
    RecommendedBookItem,
    RecommendationListResponse,
)
from backend.services.recommendation_service import (
    recommend_for_user,
    recommend_continue_reading,
    recommend_similar_books,
    load_user_recommendation_data,
    update_user_preferences,
    save_user_feedback,
    sanitize_username,
)
from book_service import get_book_by_id

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _validate_book_id(book_id: str) -> str:
    cleaned = book_id.strip()
    if not cleaned or not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã sách không hợp lệ hoặc chứa ký tự không an toàn",
        )
    return cleaned


def _map_book_to_item(book_dict: dict[str, Any]) -> RecommendedBookItem:
    return RecommendedBookItem(
        book_id=str(book_dict.get("book_id", "")),
        title=str(book_dict.get("title", "Không rõ tiêu đề")),
        author=str(book_dict.get("author", "Không rõ tác giả")),
        genre=str(book_dict.get("genre", "Tổng hợp")),
        cover_url=str(book_dict.get("cover_url", "")),
        rating=float(book_dict.get("rating", 4.0) or 4.0),
        year=book_dict.get("year"),
        pages=book_dict.get("pages", 0),
        reading_available=bool(book_dict.get("reading_available", False)),
        reading_type=str(book_dict.get("reading_type", "")),
        format=str(book_dict.get("format", "Bìa mềm")),
        score=float(book_dict.get("score", 0.0)),
        reason=str(book_dict.get("reason", "")),
        reason_type=str(book_dict.get("reason_type", "featured")),
        user_feedback=book_dict.get("user_feedback"),
    )


@router.get("/for-you", response_model=RecommendationListResponse)
def get_recommendations_for_you(
    limit: int = Query(10, ge=1, le=50, description="Số lượng sách gợi ý tối đa"),
    algorithm: str = Query("hybrid", description="Thuật toán gợi ý: 'hybrid' (kết hợp Nội dung và Cộng đồng), 'content_based', hoặc 'collaborative'"),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> RecommendationListResponse:
    username = current_user.get("username") if current_user else None
    books, basis, is_personalized = recommend_for_user(
        username=username,
        limit=limit,
        algorithm=algorithm,
    )
    items = [_map_book_to_item(b) for b in books]

    return RecommendationListResponse(
        total=len(items),
        recommendations=items,
        algorithm=algorithm,
        is_personalized=is_personalized,
        source_basis=basis,
    )


@router.get("/continue-reading", response_model=RecommendationListResponse)
def get_continue_reading_recommendations(
    limit: int = Query(6, ge=1, le=30),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationListResponse:
    username = current_user["username"]
    books = recommend_continue_reading(username=username, limit=limit)
    items = [_map_book_to_item(b) for b in books]

    return RecommendationListResponse(
        total=len(items),
        recommendations=items,
        algorithm="continue_reading_flow",
        is_personalized=True,
        source_basis="Dựa trên tiến độ các cuốn sách bạn đang đọc dở",
    )


@router.get("/similar/{book_id}", response_model=RecommendationListResponse)
def get_similar_book_recommendations(
    book_id: str,
    limit: int = Query(6, ge=1, le=30),
) -> RecommendationListResponse:
    cleaned_id = _validate_book_id(book_id)
    df = get_books_df()
    book = get_book_by_id(cleaned_id, df)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuốn sách với mã {cleaned_id}",
        )

    books = recommend_similar_books(cleaned_id, limit=limit, books_df=df)
    items = [_map_book_to_item(b) for b in books]

    return RecommendationListResponse(
        total=len(items),
        recommendations=items,
        algorithm="content_semantic_similarity",
        is_personalized=False,
        source_basis=f"Dựa trên sự tương đồng với cuốn sách '{book.get('title')}'",
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
def get_preferences(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserPreferencesResponse:
    username = current_user["username"]
    user_data = load_user_recommendation_data(username)
    prefs = user_data.get("preferences", {})
    return UserPreferencesResponse(
        username=username,
        preferred_genres=prefs.get("preferred_genres", []),
        preferred_authors=prefs.get("preferred_authors", []),
        reading_goal=prefs.get("reading_goal", ""),
        updated_at=user_data.get("updated_at", ""),
    )


@router.post("/preferences", response_model=UserPreferencesResponse)
def set_preferences(
    req: UserPreferencesUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserPreferencesResponse:
    username = current_user["username"]
    updated_prefs = update_user_preferences(
        username=username,
        preferred_genres=req.preferred_genres,
        preferred_authors=req.preferred_authors,
        reading_goal=req.reading_goal,
    )
    user_data = load_user_recommendation_data(username)
    return UserPreferencesResponse(
        username=username,
        preferred_genres=updated_prefs.get("preferred_genres", []),
        preferred_authors=updated_prefs.get("preferred_authors", []),
        reading_goal=updated_prefs.get("reading_goal", ""),
        updated_at=user_data.get("updated_at", ""),
    )


@router.post("/feedback", response_model=RecommendationFeedbackResponse)
def submit_recommendation_feedback(
    req: RecommendationFeedbackCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationFeedbackResponse:
    username = current_user["username"]
    cleaned_id = _validate_book_id(req.book_id)

    # Kiểm tra sách có tồn tại trong thư viện không
    df = get_books_df()
    book = get_book_by_id(cleaned_id, df)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sách với mã {cleaned_id}",
        )

    save_user_feedback(
        username=username,
        book_id=cleaned_id,
        liked=req.liked,
        reason=req.reason,
    )

    if req.liked is True:
        msg = f"Đã ghi nhận bạn THÍCH cuốn '{book.get('title')}'. Hệ thống sẽ gợi ý thêm sách tương tự."
    elif req.liked is False:
        msg = f"Đã ghi nhận bạn KHÔNG THÍCH cuốn '{book.get('title')}'. Cuốn sách này sẽ không xuất hiện lại trong gợi ý."
    else:
        msg = f"Đã khôi phục trạng thái cho cuốn '{book.get('title')}'."

    return RecommendationFeedbackResponse(
        success=True,
        book_id=cleaned_id,
        liked=req.liked,
        message=msg,
    )


@router.post("/refresh", response_model=RecommendationListResponse)
def refresh_recommendations(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationListResponse:
    username = current_user["username"]
    books, basis, is_personalized = recommend_for_user(username=username, limit=limit)
    items = [_map_book_to_item(b) for b in books]

    return RecommendationListResponse(
        total=len(items),
        recommendations=items,
        algorithm="hybrid_content_semantic",
        is_personalized=is_personalized,
        source_basis=f"Đã làm mới gợi ý: {basis}",
    )

