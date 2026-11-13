from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from backend.core.database import get_books_df, get_authors_df, get_genres_df
from backend.schemas.book_schema import BookOut

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/stats")
def get_home_stats() -> dict[str, Any]:
    books_df = get_books_df()
    authors_df = get_authors_df()
    genres_df = get_genres_df()

    total_books = len(books_df)
    total_authors = len(authors_df)
    total_genres = len(genres_df)

    # Online reading count
    if not books_df.empty and "reading_available" in books_df.columns:
        online_reading_count = int(
            (books_df["reading_available"].astype(str).str.lower().isin(["true", "1"])).sum()
        )
    else:
        online_reading_count = 0

    # Featured books
    featured_books: list[dict[str, Any]] = []
    if not books_df.empty and "featured" in books_df.columns:
        feat_df = books_df[books_df["featured"].astype(str).str.lower().isin(["true", "1"])].head(6)
        featured_books = feat_df.to_dict(orient="records")

    return {
        "total_books": total_books,
        "total_authors": total_authors,
        "total_genres": total_genres,
        "online_reading_count": online_reading_count,
        "featured_books": featured_books,
    }

