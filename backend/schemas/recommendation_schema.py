from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class UserPreferencesUpdate(BaseModel):
    preferred_genres: list[str] = Field(default_factory=list, description="Danh sách thể loại người dùng quan tâm")
    preferred_authors: list[str] = Field(default_factory=list, description="Danh sách tác giả người dùng ưa thích")
    reading_goal: str = Field("", description="Mục tiêu hoặc định hướng đọc sách")


class UserPreferencesResponse(BaseModel):
    username: str
    preferred_genres: list[str]
    preferred_authors: list[str]
    reading_goal: str
    updated_at: str


class RecommendationFeedbackCreate(BaseModel):
    book_id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Mã sách hợp lệ")
    liked: bool | None = Field(None, description="True: Like, False: Dislike, None: Hủy đánh giá/Khôi phục")
    reason: str = Field("", description="Lý do phản hồi nếu có")


class RecommendationFeedbackResponse(BaseModel):
    success: bool
    book_id: str
    liked: bool | None
    message: str


class RecommendedBookItem(BaseModel):
    book_id: str
    title: str
    author: str
    genre: str
    cover_url: str = ""
    rating: float = 4.0
    year: Any = None
    pages: Any = 0
    reading_available: bool = False
    reading_type: str = ""
    format: str = "Bìa mềm"
    score: float = 0.0
    reason: str = ""
    reason_type: str = "featured"
    user_feedback: str | None = None


class RecommendationListResponse(BaseModel):
    total: int
    recommendations: list[RecommendedBookItem]
    algorithm: str = "hybrid_content_semantic"
    is_personalized: bool = True
    source_basis: str = ""

