from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from backend.core.database import get_genres_df, get_books_df
from backend.schemas.genre_schema import GenreOut

router = APIRouter(prefix="/genres", tags=["Genres"])


@router.get("", response_model=list[dict[str, Any]])
def list_genres() -> list[dict[str, Any]]:
    genres_df = get_genres_df()
    books_df = get_books_df()

    genre_counts: dict[str, int] = {}
    if not books_df.empty and "genre" in books_df.columns:
        genre_counts = books_df["genre"].astype(str).str.strip().value_counts().to_dict()

    results: list[dict[str, Any]] = []
    if not genres_df.empty:
        for _, row in genres_df.iterrows():
            g_dict = row.to_dict()
            name = str(g_dict.get("name", ""))
            count = genre_counts.get(name, 0)
            results.append({
                "genre_id": g_dict.get("genre_id", ""),
                "name": name,
                "description": g_dict.get("description", ""),
                "icon": g_dict.get("icon", ""),
                "book_count": count,
            })
    else:
        # Fallback to genres in books_df
        for genre_name, count in genre_counts.items():
            results.append({
                "genre_id": genre_name.lower().replace(" ", "-"),
                "name": genre_name,
                "description": "",
                "icon": "menu_book",
                "book_count": count,
            })

    return results

