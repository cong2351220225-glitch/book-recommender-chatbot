from __future__ import annotations

from pydantic import BaseModel


class GenreOut(BaseModel):
    genre: str
    book_count: int = 0

