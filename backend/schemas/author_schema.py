from __future__ import annotations

from typing import Any
from pydantic import BaseModel
from backend.schemas.book_schema import BookOut


class AuthorOut(BaseModel):
    author_id: str
    name: str = ""
    bio: str = ""
    birth_year: Any = None
    death_year: Any = None
    nationality: str = ""
    work_count: int = 0
    genres: list[str] = []


class AuthorDetailResponse(BaseModel):
    author: AuthorOut
    books: list[BookOut] = []

