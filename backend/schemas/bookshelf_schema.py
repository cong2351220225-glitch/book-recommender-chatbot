from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BookshelfItemCreate(BaseModel):
    book_id: str = Field(..., description="ID của cuốn sách cần thêm vào tủ")
    status: str = Field(
        ...,
        description="Trạng thái trong tủ: 'favorite' (Yêu thích), 'reading' (Đang đọc), 'completed' (Đã đọc)",
    )
    progress_page: int = Field(0, ge=0, description="Trang đang đọc hiện tại")
    total_pages: int = Field(0, ge=0, description="Tổng số trang của sách")
    rating: int = Field(0, ge=0, le=5, description="Đánh giá của người dùng từ 1-5 sao")
    notes: str = Field("", description="Ghi chú cá nhân của người dùng")


class BookshelfItemUpdate(BaseModel):
    status: str | None = Field(
        None,
        description="Trạng thái mới: 'favorite', 'reading', 'completed'",
    )
    progress_page: int | None = Field(None, ge=0, description="Trang đang đọc")
    total_pages: int | None = Field(None, ge=0, description="Tổng số trang")
    rating: int | None = Field(None, ge=0, le=5, description="Đánh giá 1-5 sao")
    notes: str | None = Field(None, description="Ghi chú cá nhân")


class BookshelfItemResponse(BaseModel):
    id: str
    book_id: str
    status: str
    progress_page: int = 0
    total_pages: int = 0
    rating: int = 0
    notes: str = ""
    added_at: str
    updated_at: str
    book: dict[str, Any] = {}


class BookshelfListResponse(BaseModel):
    total: int
    items: list[BookshelfItemResponse]


class BookshelfCheckResponse(BaseModel):
    book_id: str
    in_bookshelf: bool
    statuses: list[str] = []
    items: list[BookshelfItemResponse] = []

