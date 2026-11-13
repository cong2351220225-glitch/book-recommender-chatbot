from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BookOut(BaseModel):
    book_id: str
    title: str = ""
    author: str = ""
    author_id: str = ""
    genre: str = ""
    description: str = ""
    year: Any = None
    isbn: str = ""
    publisher: str = ""
    pages: Any = None
    language: str = ""
    format: str = ""
    cover_url: str = ""
    rating: Any = None
    featured: Any = False
    tags: str = ""
    target_audience: str = ""
    mood: str = ""
    difficulty: str = ""
    summary: str = ""
    reading_available: Any = False
    reading_type: str = ""
    reading_url: str = ""
    local_file: str = ""
    purchase_url: str = ""
    library_url: str = ""


class BookListResponse(BaseModel):
    items: list[BookOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class BookDetailResponse(BaseModel):
    book: BookOut
    related_books: list[BookOut] = []
    reading_status: str = ""
    can_read: bool = False


class BookSummaryRequest(BaseModel):
    summary_type: str = Field("short", description="'short' (ngắn gọn) hoặc 'detailed' (chi tiết chuyên sâu)")


class BookSummaryResponse(BaseModel):
    book_id: str
    title: str
    author: str
    source_type: str = Field(..., description="'full_text' (toàn văn thực tế) hoặc 'metadata' (giới thiệu/mô tả)")
    summary: str
    has_full_text: bool
    notice: str = ""


class BookQARequest(BaseModel):
    question: str = Field(..., min_length=1, description="Câu hỏi dành riêng cho cuốn sách được chọn")


class BookQAResponse(BaseModel):
    book_id: str
    title: str
    author: str
    question: str
    answer: str
    context_source: str = Field(..., description="'full_text' hoặc 'metadata'")
    has_sufficient_context: bool = True


