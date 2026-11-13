from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from backend.core.database import get_authors_df, get_books_df
from backend.schemas.author_schema import AuthorOut, AuthorDetailResponse
from backend.schemas.book_schema import BookOut
from author_service import (
    search_authors,
    get_author_by_id,
    get_author_work_count,
    get_author_genres,
    get_author_books,
)

router = APIRouter(prefix="/authors", tags=["Authors"])


@router.get("", response_model=list[AuthorOut])
def list_authors(q: str | None = Query(None, description="Search author by name")) -> list[AuthorOut]:
    authors_df = get_authors_df()
    books_df = get_books_df()

    if q and q.strip():
        authors_df = search_authors(authors_df, query=q.strip())

    results: list[AuthorOut] = []
    for _, row in authors_df.iterrows():
        a_dict = row.to_dict()
        author_id = str(a_dict.get("author_id", ""))
        name = str(a_dict.get("name", ""))
        work_count = get_author_work_count(books_df, author_id or name, authors_df)
        genres = get_author_genres(books_df, author_id or name, authors_df)
        results.append(
            AuthorOut(
                author_id=author_id,
                name=name,
                bio=str(a_dict.get("bio", "")),
                birth_year=a_dict.get("birth_year") if a_dict.get("birth_year") != "" else None,
                death_year=a_dict.get("death_year") if a_dict.get("death_year") != "" else None,
                nationality=str(a_dict.get("nationality", "")),
                work_count=work_count,
                genres=genres,
            )
        )
    return results


@router.get("/{author_id}", response_model=AuthorDetailResponse)
def get_author_detail(author_id: str) -> AuthorDetailResponse:
    authors_df = get_authors_df()
    books_df = get_books_df()

    author_rec = get_author_by_id(authors_df, author_id)
    if not author_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Author with id '{author_id}' not found",
        )

    work_count = get_author_work_count(books_df, author_id, authors_df)
    genres = get_author_genres(books_df, author_id, authors_df)
    author_out = AuthorOut(
        author_id=str(author_rec.get("author_id", "")),
        name=str(author_rec.get("name", "")),
        bio=str(author_rec.get("bio", "")),
        birth_year=author_rec.get("birth_year") if author_rec.get("birth_year") != "" else None,
        death_year=author_rec.get("death_year") if author_rec.get("death_year") != "" else None,
        nationality=str(author_rec.get("nationality", "")),
        work_count=work_count,
        genres=genres,
    )

    author_books_df = get_author_books(books_df, author_id, authors_df)
    books_list = [BookOut(**r) for r in author_books_df.to_dict(orient="records")] if not author_books_df.empty else []

    return AuthorDetailResponse(
        author=author_out,
        books=books_list,
    )

