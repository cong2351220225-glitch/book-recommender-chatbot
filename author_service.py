from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
AUTHORS_PATH = BASE_DIR / "data" / "authors.csv"


def normalize_search_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_authors(path: Path = AUTHORS_PATH) -> pd.DataFrame:
    """Load author metadata from CSV, preserving empty fields in a safe way."""
    if not path.exists():
        return pd.DataFrame(columns=["author_id", "name", "bio", "nationality", "birth_year", "death_year", "photo_url", "website", "featured"])
    authors = pd.read_csv(path).fillna("")
    for missing_field in ("author_id", "name"):
        if missing_field not in authors.columns:
            authors[missing_field] = ""
    if "featured" not in authors.columns:
        authors["featured"] = False
    authors["featured"] = authors["featured"].astype(str).str.lower().isin(("true", "1", "yes", "co", "có"))
    authors["author_id"] = authors["author_id"].astype(str).str.strip()
    authors["name"] = authors["name"].astype(str).str.strip()
    return authors.reset_index(drop=True)


def get_all_authors() -> pd.DataFrame:
    return load_authors()


def search_authors(authors: pd.DataFrame | None = None, query: str = "") -> pd.DataFrame:
    """Search authors by name while handling empty queries and Vietnamese names safely."""
    dataset = load_authors() if authors is None else authors
    if not query or not str(query).strip():
        return dataset.copy().reset_index(drop=True)
    query_text = normalize_search_text(query)
    if not query_text:
        return dataset.copy().reset_index(drop=True)
    mask = dataset["name"].fillna("").astype(str).map(normalize_search_text).str.contains(query_text, regex=False, na=False)
    return dataset[mask].reset_index(drop=True)


def get_author(authors: pd.DataFrame, author_id: str | None = None, author_name: str | None = None) -> dict[str, Any] | None:
    """Get a single author by ID or name from the dataset."""
    dataset = load_authors() if authors is None else authors
    if author_id is not None:
        matches = dataset[dataset["author_id"].astype(str).str.lower() == str(author_id).strip().lower()]
        if not matches.empty:
            return matches.iloc[0].to_dict()
    if author_name is not None:
        matches = dataset[dataset["name"].fillna("").astype(str).str.lower().str.contains(str(author_name).strip().lower(), regex=False, na=False)]
        if not matches.empty:
            return matches.iloc[0].to_dict()
    return None


def get_author_by_id(authors: pd.DataFrame, author_id: str) -> dict[str, Any] | None:
    return get_author(authors, author_id=author_id)


def get_author_by_name(authors: pd.DataFrame, name: str) -> dict[str, Any] | None:
    return get_author(authors, author_name=name)


def find_authors(authors: pd.DataFrame | None = None, query: str = "") -> pd.DataFrame:
    return search_authors(authors, query)


def get_author_books(books: pd.DataFrame, author_id_or_name: str, authors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return all books linked to an author ID or author name."""
    dataset = books if books is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    author_key = str(author_id_or_name).strip()
    author_match = None
    if authors is not None:
        author_match = get_author(authors, author_id=author_key) or get_author(authors, author_name=author_key)
    if author_match is not None and author_match.get("author_id"):
        author_key = str(author_match["author_id"])
    matches = dataset[
        (dataset["author_id"].astype(str).str.lower() == author_key.lower())
        | dataset["author"].fillna("").astype(str).str.lower().str.contains(author_key.lower(), regex=False, na=False)
    ]
    return matches.reset_index(drop=True)


def get_author_work_count(books: pd.DataFrame, author_id_or_name: str, authors: pd.DataFrame | None = None) -> int:
    return len(get_author_books(books, author_id_or_name, authors))


def get_author_genres(books: pd.DataFrame, author_id_or_name: str, authors: pd.DataFrame | None = None) -> list[str]:
    author_books = get_author_books(books, author_id_or_name, authors)
    return sorted({str(value).strip() for value in author_books["genre"].dropna().tolist() if str(value).strip()})


def get_featured_works(books: pd.DataFrame, author_id: str) -> pd.DataFrame:
    return books[(books["author_id"].astype(str) == str(author_id)) & books["featured"]].reset_index(drop=True)
