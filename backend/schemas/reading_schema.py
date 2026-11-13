from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ReadingProgressCreate(BaseModel):
    book_id: str = Field(..., description="Mã sách cần lưu tiến độ đọc")
    current_page: int = Field(1, ge=1, description="Trang đang đọc hiện tại")
    total_pages: int = Field(1, ge=1, description="Tổng số trang của tài liệu")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="Phần trăm đã đọc (0-100%)")
    last_read_location: str = Field("", description="Vị trí/chương đang đọc dở")


class ReadingProgressResponse(BaseModel):
    book_id: str
    current_page: int
    total_pages: int
    progress_percent: float
    last_read_location: str = ""
    updated_at: str


class ReadingDocInfoResponse(BaseModel):
    book_id: str
    title: str
    author: str = ""
    can_read: bool
    format: str = "none"  # "pdf", "epub", "none"
    file_size_bytes: int = 0
    file_url: str = ""
    saved_progress: ReadingProgressResponse | None = None

