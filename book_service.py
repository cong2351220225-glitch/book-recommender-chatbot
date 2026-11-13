from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
BOOKS_PATH = BASE_DIR / "data" / "books.csv"
BOOK_FIELDS = [
    "book_id", "title", "author", "author_id", "genre", "description", "year", "isbn",
    "publisher", "pages", "language", "format", "cover_url", "rating", "featured", "tags",
    "target_audience", "mood", "difficulty", "summary", "reading_available", "reading_type",
    "reading_url", "local_file", "purchase_url", "library_url",
]
DEFAULTS: dict[str, Any] = {
    "author_id": "", "isbn": "", "publisher": "", "pages": 0, "language": "Tiếng Việt",
    "format": "Bìa mềm", "cover_url": "", "rating": 4.2, "featured": False, "tags": "",
    "target_audience": "Độc giả phổ thông", "mood": "Muốn học hỏi", "difficulty": "Dễ đọc",
    "summary": "", "reading_available": False, "reading_type": "", "reading_url": "",
    "local_file": "", "purchase_url": "", "library_url": "",
}


def normalize_search_text(value: Any) -> str:
    """Normalize text for case-insensitive, whitespace-tolerant search in Vietnamese content."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("đ", "d")
    text = text.replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_books(path: Path = BOOKS_PATH) -> pd.DataFrame:
    """Load the books dataset and coerce the schema to a stable, safe shape."""
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy dữ liệu sách: {path}")
    books = pd.read_csv(path).fillna("")
    for field, default in DEFAULTS.items():
        if field not in books.columns:
            books[field] = default
    if "book_id" not in books.columns:
        books.insert(0, "book_id", [f"book_{index:03d}" for index in range(1, len(books) + 1)])
    for field in ("title", "author", "genre", "description", "summary", "tags"):
        books[field] = books[field].fillna("").astype(str).str.strip()
    books["summary"] = books["summary"].where(books["summary"] != "", books["description"])
    books["year"] = pd.to_numeric(books["year"], errors="coerce").fillna(0).astype(int)
    books["rating"] = pd.to_numeric(books["rating"], errors="coerce").fillna(4.0).astype(float)
    books["pages"] = pd.to_numeric(books["pages"], errors="coerce").fillna(0).astype(int)
    books["featured"] = books["featured"].astype(str).str.lower().isin(("true", "1", "yes", "co", "có"))
    books["reading_available"] = books["reading_available"].astype(str).str.lower().isin(("true", "1", "yes", "co", "có"))
    return books[BOOK_FIELDS].reset_index(drop=True)


def get_all_books() -> pd.DataFrame:
    """Return all books in the library dataset."""
    return load_books()


def get_book_by_id(book_id: str, books: pd.DataFrame | None = None) -> dict[str, Any] | None:
    """Fetch a single book by ID, with a safe fallback for missing data."""
    dataset = books if books is not None else load_books()
    matches = dataset[dataset["book_id"].astype(str) == str(book_id)]
    return matches.iloc[0].to_dict() if not matches.empty else None


def get_book(books: pd.DataFrame, book_id: str) -> dict[str, Any] | None:
    return get_book_by_id(book_id, books)


def get_available_genres(books: pd.DataFrame | None = None) -> list[str]:
    dataset = books if books is not None else load_books()
    return sorted({str(value).strip() for value in dataset["genre"].dropna().tolist() if str(value).strip()})


def get_available_authors(books: pd.DataFrame | None = None) -> list[str]:
    dataset = books if books is not None else load_books()
    return sorted({str(value).strip() for value in dataset["author"].dropna().tolist() if str(value).strip()})


def get_available_years(books: pd.DataFrame | None = None) -> list[int]:
    dataset = books if books is not None else load_books()
    years = pd.to_numeric(dataset["year"], errors="coerce").dropna().astype(int)
    return sorted(set(years.tolist()))


def get_featured_books(books: pd.DataFrame | None = None, limit: int = 6) -> pd.DataFrame:
    dataset = books if books is not None else load_books()
    return dataset[dataset["featured"]].sort_values(["rating", "year"], ascending=False).head(limit).reset_index(drop=True)


def get_related_books(books: pd.DataFrame | None, book: dict[str, Any] | str, limit: int = 5) -> pd.DataFrame:
    """Return related books using matching genre/tag information and a simple similarity score."""
    dataset = books if books is not None else load_books()
    if isinstance(book, str):
        candidate = get_book_by_id(book, dataset)
        if candidate is None:
            return pd.DataFrame(columns=dataset.columns)
        book = candidate
    book_id = str(book.get("book_id", ""))
    candidates = dataset[dataset["book_id"].astype(str) != book_id].copy()
    if candidates.empty:
        return candidates.reset_index(drop=True)
    tags = {normalize_search_text(tag) for tag in str(book.get("tags", "")).split(",") if normalize_search_text(tag)}
    candidates["score"] = candidates.apply(
        lambda row: (2 if str(row.get("genre", "")) == str(book.get("genre", "")) else 0)
        + sum(1 for tag in tags if normalize_search_text(row.get("tags", "")) and normalize_search_text(tag) in normalize_search_text(row.get("tags", "")))
        + (1 if str(row.get("author", "")) == str(book.get("author", "")) else 0),
        axis=1,
    )
    return candidates.sort_values(["score", "rating"], ascending=False).head(limit).drop(columns=["score"], errors="ignore").reset_index(drop=True)


def filter_books(
    books: pd.DataFrame | None = None,
    genre: str | None = None,
    author: str | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    """Filter books by genre, author or publication year with safe defaults."""
    dataset = books if books is not None else load_books()
    filtered = dataset.copy()
    if genre:
        filtered = filtered[filtered["genre"].astype(str).str.lower() == str(genre).strip().lower()]
    if author:
        author_text = str(author).strip().lower()
        filtered = filtered[
            filtered["author"].astype(str).str.lower().str.contains(author_text, regex=False, na=False)
            | filtered["author_id"].astype(str).str.lower().str.contains(author_text, regex=False, na=False)
        ]
    if year is not None:
        filtered = filtered[filtered["year"] == int(year)]
    return filtered.reset_index(drop=True)


def get_books_by_author(books: pd.DataFrame | None, author: str) -> pd.DataFrame:
    dataset = books if books is not None else load_books()
    author_text = str(author).strip().lower()
    matches = dataset[
        dataset["author"].astype(str).str.lower().str.contains(author_text, regex=False, na=False)
        | dataset["author_id"].astype(str).str.lower().str.contains(author_text, regex=False, na=False)
    ]
    return matches.reset_index(drop=True)


def get_books_by_genre(books: pd.DataFrame | None, genre: str) -> pd.DataFrame:
    dataset = books if books is not None else load_books()
    return dataset[dataset["genre"].astype(str).str.lower() == str(genre).strip().lower()].reset_index(drop=True)


def search_books(
    books: pd.DataFrame | None = None,
    query: str = "",
    genre: str = "Tất cả",
    author: str = "Tất cả",
    year_range: tuple[int, int] | None = None,
    language: str = "Tất cả",
    min_rating: float = 0.0,
    featured_only: bool = False,
    sort_by: str = "Phù hợp",
) -> pd.DataFrame:
    """Search books by natural-language keywords, while remaining safe for empty or missing values."""
    dataset = books if books is not None else load_books()
    filtered = dataset.copy()
    normalized_query = normalize_search_text(query)
    if normalized_query:
        searchable = filtered[["title", "author", "isbn", "genre", "description", "summary", "tags"]].fillna("").astype(str)
        terms = searchable.agg(lambda row: " ".join(row), axis=1)
        normalized_terms = terms.map(normalize_search_text)
        filtered = filtered[normalized_terms.str.contains(normalized_query, regex=False, na=False)]
    if genre and str(genre).strip() not in {"", "Tất cả"}:
        filtered = filtered[filtered["genre"].astype(str).str.lower() == str(genre).strip().lower()]
    if author and str(author).strip() not in {"", "Tất cả"}:
        author_value = str(author).strip().lower()
        filtered = filtered[
            filtered["author"].astype(str).str.lower().str.contains(author_value, regex=False, na=False)
            | filtered["author_id"].astype(str).str.lower().str.contains(author_value, regex=False, na=False)
        ]
    if language and str(language).strip() not in {"", "Tất cả"}:
        filtered = filtered[filtered["language"].astype(str).str.lower() == str(language).strip().lower()]
    if year_range:
        start_year, end_year = year_range
        filtered = filtered[filtered["year"].between(int(start_year), int(end_year))]
    if min_rating:
        filtered = filtered[filtered["rating"] >= float(min_rating)]
    if featured_only:
        filtered = filtered[filtered["featured"] == True]
    sort_specs = {
        "Tên A-Z": (["title"], [True]),
        "Tên Z-A": (["title"], [False]),
        "Năm mới nhất": (["year", "title"], [False, True]),
        "Năm cũ nhất": (["year", "title"], [True, True]),
        "Đánh giá cao": (["rating", "title"], [False, True]),
        "Đánh giá thấp": (["rating", "title"], [True, True]),
        "Phù hợp": (["featured", "rating", "title"], [False, False, True]),
    }
    if sort_by in sort_specs:
        cols, asc = sort_specs[sort_by]
        return filtered.sort_values(cols, ascending=asc, kind="stable").reset_index(drop=True)
    return filtered.sort_values(["title"], ascending=[True], kind="stable").reset_index(drop=True)


def get_book_count(books: pd.DataFrame | None = None) -> int:
    dataset = books if books is not None else load_books()
    return int(len(dataset))


def purchase_search_url(title: str) -> str:
    return f"https://www.google.com/search?q={quote_plus((title or 'sách').strip() + ' mua sách')}"
