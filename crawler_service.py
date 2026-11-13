"""AI Crawler Service — Multi-source connectors for AI Digital Library.

Provides search, normalization, duplicate detection, CSV append, and
incremental ChromaDB upsert.

Supported authoritative open sources:
1. Open Library API (no auth)
2. Google Books API (public or via GOOGLE_BOOKS_API_KEY)
3. Project Gutenberg / Gutendex (Public domain ebooks, full-text reading available)
4. Internet Archive (Metadata, digital texts, archive view url)
5. Europeana API (Digital heritage books via EUROPEANA_API_KEY)
6. iTunes / Apple Books (VN market commercial ebooks, preview/purchase url)

Design constraints:
- Conforms strictly to the 26-column schema of data/books.csv.
- Individual connector failure or timeout NEVER breaks the overall search.
- Clean distinction between public domain (reading_available=True) and metadata/purchase.
- Safe duplicate detection & incremental ChromaDB upserting.
"""

from __future__ import annotations

import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
BOOKS_CSV_PATH = BASE_DIR / "data" / "books.csv"
COLLECTION_NAME = "books_collection"
EMBEDDING_MODEL = "gemini-embedding-2"

load_dotenv(BASE_DIR / ".env")

# Matches the 26 columns in book_service.BOOK_FIELDS
BOOK_FIELDS = [
    "book_id", "title", "author", "author_id", "genre", "description",
    "year", "isbn", "publisher", "pages", "language", "format",
    "cover_url", "rating", "featured", "tags", "target_audience",
    "mood", "difficulty", "summary", "reading_available", "reading_type",
    "reading_url", "local_file", "purchase_url", "library_url",
]
FIELD_DEFAULTS: dict[str, Any] = {
    "author_id": "", "isbn": "", "publisher": "", "pages": 0,
    "language": "Tiếng Việt", "format": "Bìa mềm", "cover_url": "",
    "rating": 4.0, "featured": False, "tags": "",
    "target_audience": "Mọi độc giả", "mood": "Muốn học hỏi",
    "difficulty": "Trung bình", "summary": "", "reading_available": False,
    "reading_type": "", "reading_url": "", "local_file": "",
    "purchase_url": "", "library_url": "",
}

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _normalize(value: Any) -> str:
    """Case/accent-insensitive normalisation."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def _clean_isbn(isbn_val: str) -> str:
    """Normalize ISBN string to digits and X only."""
    if not isbn_val:
        return ""
    cleaned = re.sub(r"[^0-9X]", "", str(isbn_val).upper())
    return cleaned if len(cleaned) in (10, 13) else str(isbn_val).strip()


def _next_book_id(existing_df: pd.DataFrame) -> str:
    """Return the next sequential book_NNNNN id not present in existing_df."""
    used_ids = set(existing_df["book_id"].astype(str).tolist()) if not existing_df.empty else set()
    n = len(used_ids) + 1
    while True:
        candidate = f"book_{n:03d}"
        if candidate not in used_ids:
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# 1. Open Library Connector
# ---------------------------------------------------------------------------

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
OPEN_LIBRARY_BOOK_URL = "https://openlibrary.org{key}"

_OL_GENRE_MAP: dict[str, str] = {
    "psychology": "Tâm lý", "self-help": "Kỹ năng sống", "business": "Kinh doanh",
    "economics": "Kinh tế", "fiction": "Tiểu thuyết", "novel": "Tiểu thuyết",
    "history": "Lịch sử", "science": "Khoa học", "philosophy": "Triết học",
    "health": "Sức khỏe", "education": "Giáo dục", "management": "Quản trị",
    "marketing": "Marketing", "finance": "Tài chính", "technology": "Công nghệ",
    "computers": "Công nghệ", "programming": "Công nghệ", "literature": "Văn học",
    "biography": "Tiểu sử", "children": "Thiếu nhi", "travel": "Du lịch",
    "cooking": "Nấu ăn", "art": "Nghệ thuật", "religion": "Tôn giáo",
}


def _map_ol_genre(subjects: list[str]) -> str:
    for subject in subjects:
        key = _normalize(subject)
        for eng, vie in _OL_GENRE_MAP.items():
            if eng in key:
                return vie
    return subjects[0].title() if subjects else "Tổng hợp"


def search_open_library(
    query: str = "",
    author: str = "",
    subject: str = "",
    isbn: str = "",
    language: str = "",
    year_from: int = 0,
    year_to: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Search Open Library Search API with error isolation."""
    params: dict[str, Any] = {
        "limit": min(limit, 100),
        "fields": ",".join([
            "key", "title", "author_name", "isbn", "first_publish_year",
            "subject", "language", "number_of_pages_median", "cover_i",
            "publisher", "ratings_average",
        ]),
    }
    parts = []
    if query.strip():
        parts.append(query.strip())
    if author.strip():
        params["author"] = author.strip()
    if subject.strip():
        params["subject"] = subject.strip()
    if isbn.strip():
        params["isbn"] = _clean_isbn(isbn.strip())
    if year_from and year_to:
        params["publish_year"] = f"[{year_from} TO {year_to}]"
    elif year_from:
        params["publish_year"] = str(year_from)
    if language.strip():
        params["language"] = language.strip()
    if parts:
        params["q"] = " ".join(parts)
    elif not any(k in params for k in ("isbn", "author", "subject")):
        params["q"] = "*"

    try:
        resp = requests.get(OPEN_LIBRARY_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("Open Library search failed: %s", exc)
        return []

    results = []
    for doc in data.get("docs", []):
        authors_list: list[str] = doc.get("author_name") or []
        subjects_list: list[str] = doc.get("subject") or []
        isbn_list: list[str] = doc.get("isbn") or []
        lang_list: list[str] = doc.get("language") or []
        publishers_list: list[str] = doc.get("publisher") or []
        cover_i = doc.get("cover_i")
        cover_url = OPEN_LIBRARY_COVER.format(cover_id=cover_i) if cover_i else ""
        library_url = OPEN_LIBRARY_BOOK_URL.format(key=doc.get("key", "")) if doc.get("key") else ""
        year = doc.get("first_publish_year") or 0
        rating_raw = doc.get("ratings_average") or 0.0

        results.append({
            "_source": "Open Library",
            "_raw_id": doc.get("key", ""),
            "title": str(doc.get("title", "")).strip(),
            "author": ", ".join(authors_list[:2]) if authors_list else "Không rõ tác giả",
            "genre_raw": subjects_list,
            "year": int(year) if year else 0,
            "isbn": _clean_isbn(isbn_list[0]) if isbn_list else "",
            "publisher": publishers_list[0] if publishers_list else "",
            "pages": int(doc.get("number_of_pages_median") or 0),
            "language": lang_list[0] if lang_list else "eng",
            "cover_url": cover_url,
            "rating": round(float(rating_raw), 1) if rating_raw else 4.0,
            "library_url": library_url,
            "reading_available": False,
            "reading_type": "",
            "reading_url": "",
        })
    return results


# ---------------------------------------------------------------------------
# 2. Google Books Connector
# ---------------------------------------------------------------------------

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

def search_google_books(
    query: str = "",
    author: str = "",
    subject: str = "",
    isbn: str = "",
    language: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search Google Books API (handles API key and public queries)."""
    q_parts = []
    if query.strip():
        q_parts.append(query.strip())
    if author.strip():
        q_parts.append(f"inauthor:{author.strip()}")
    if subject.strip():
        q_parts.append(f"subject:{subject.strip()}")
    if isbn.strip():
        q_parts.append(f"isbn:{_clean_isbn(isbn.strip())}")

    q_string = " ".join(q_parts).strip()
    if not q_string:
        return []

    params: dict[str, Any] = {
        "q": q_string,
        "maxResults": min(limit, 40),
        "printType": "books",
    }
    if language.strip():
        params["langRestrict"] = language.strip()

    api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    if api_key and not api_key.startswith("your_"):
        params["key"] = api_key

    try:
        resp = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=12)
        if resp.status_code == 429:
            LOGGER.warning("Google Books API rate limit exceeded (HTTP 429).")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("Google Books request failed: %s", exc)
        return []

    results = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        authors = info.get("authors", [])
        categories = info.get("categories", [])
        images = info.get("imageLinks", {})
        cover_url = images.get("thumbnail") or images.get("smallThumbnail") or ""
        if cover_url.startswith("http://"):
            cover_url = "https://" + cover_url[7:]

        isbns = [
            id_entry.get("identifier", "")
            for id_entry in info.get("industryIdentifiers", [])
            if id_entry.get("type") in ("ISBN_13", "ISBN_10")
        ]
        isbn_val = _clean_isbn(isbns[0]) if isbns else ""

        year = 0
        published_date = str(info.get("publishedDate", ""))
        if published_date and published_date[:4].isdigit():
            year = int(published_date[:4])

        access = item.get("accessInfo", {})
        web_reader_link = access.get("webReaderLink", "")
        pdf_avail = access.get("pdf", {}).get("isAvailable", False)
        viewability = access.get("viewability", "")
        reading_available = viewability in ("FULL_PUBLIC_DOMAIN", "ALL_PAGES")
        info_link = info.get("infoLink", "") or item.get("selfLink", "")

        results.append({
            "_source": "Google Books",
            "_raw_id": item.get("id", ""),
            "title": str(info.get("title", "")).strip(),
            "author": ", ".join(authors) if authors else "Không rõ tác giả",
            "genre_raw": categories,
            "year": year,
            "isbn": isbn_val,
            "publisher": str(info.get("publisher", "")).strip(),
            "pages": int(info.get("pageCount") or 0),
            "language": str(info.get("language", "vi")),
            "cover_url": cover_url,
            "rating": float(info.get("averageRating", 4.0) or 4.0),
            "description_raw": _strip_html(info.get("description", "")),
            "library_url": info_link,
            "purchase_url": item.get("saleInfo", {}).get("buyLink", ""),
            "reading_available": reading_available,
            "reading_type": "PDF/Web" if reading_available else "",
            "reading_url": web_reader_link if reading_available else "",
        })
    return results


# ---------------------------------------------------------------------------
# 3. Project Gutenberg Connector (via Gutendex Open API)
# ---------------------------------------------------------------------------

GUTENDEX_URL = "https://gutendex.com/books"

def search_project_gutenberg(
    query: str = "",
    author: str = "",
    subject: str = "",
    language: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search Project Gutenberg public domain ebooks (100% legal full text reading)."""
    search_terms = " ".join(filter(None, [query, author])).strip()
    if not search_terms and not subject:
        return []

    params: dict[str, Any] = {}
    if search_terms:
        params["search"] = search_terms
    if subject.strip():
        params["topic"] = subject.strip()
    if language.strip():
        params["languages"] = language.strip()

    try:
        resp = requests.get(GUTENDEX_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("Project Gutenberg request failed: %s", exc)
        return []

    results = []
    for book in data.get("results", [])[:limit]:
        authors = [a.get("name", "") for a in book.get("authors", [])]
        formats = book.get("formats", {})
        cover_url = formats.get("image/jpeg", "")
        # Full text online reading link
        reading_url = (
            formats.get("text/html")
            or formats.get("text/html; charset=utf-8")
            or formats.get("text/plain; charset=utf-8")
            or formats.get("application/epub+zip")
            or ""
        )
        subjects = book.get("subjects", [])
        languages = book.get("languages", ["en"])
        gut_id = book.get("id", "")
        gutenberg_url = f"https://www.gutenberg.org/ebooks/{gut_id}" if gut_id else ""

        results.append({
            "_source": "Project Gutenberg",
            "_raw_id": str(gut_id),
            "title": str(book.get("title", "")).strip(),
            "author": ", ".join(authors) if authors else "Không rõ tác giả",
            "genre_raw": subjects,
            "year": 0,
            "isbn": "",
            "publisher": "Project Gutenberg (Public Domain)",
            "pages": 0,
            "language": languages[0] if languages else "en",
            "cover_url": cover_url,
            "rating": 4.5,
            "description_raw": f"Tác phẩm văn học kinh điển thuộc phạm vi công cộng (Public Domain) do Project Gutenberg bảo tồn. Độc giả có thể đọc và tải toàn văn miễn phí hợp pháp.",
            "library_url": gutenberg_url,
            "purchase_url": "",
            "reading_available": bool(reading_url),
            "reading_type": "Public Domain (Đọc toàn văn)",
            "reading_url": reading_url,
        })
    return results


# ---------------------------------------------------------------------------
# 4. Internet Archive Connector (Open Search API)
# ---------------------------------------------------------------------------

INTERNET_ARCHIVE_URL = "https://archive.org/advancedsearch.php"

def search_internet_archive(
    query: str = "",
    author: str = "",
    subject: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search Internet Archive open digital texts and media."""
    terms = ["mediatype:texts"]
    if query.strip():
        terms.append(f"title:({query.strip()})")
    if author.strip():
        terms.append(f"creator:({author.strip()})")
    if subject.strip():
        terms.append(f"subject:({subject.strip()})")

    if len(terms) == 1:
        return []

    q_str = " AND ".join(terms)
    params = {
        "q": q_str,
        "fl[]": "identifier,title,creator,year,description,language,publicdate",
        "output": "json",
        "rows": min(limit, 50),
    }

    try:
        resp = requests.get(INTERNET_ARCHIVE_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("Internet Archive request failed: %s", exc)
        return []

    results = []
    for doc in data.get("response", {}).get("docs", []):
        ident = doc.get("identifier", "")
        if not ident:
            continue
        cover_url = f"https://archive.org/services/img/{ident}"
        ia_link = f"https://archive.org/details/{ident}"
        creator = doc.get("creator", "Không rõ tác giả")
        if isinstance(creator, list):
            creator = ", ".join(creator[:2])
        year_val = doc.get("year", 0)
        try:
            year_int = int(year_val)
        except (ValueError, TypeError):
            year_int = 0

        desc = doc.get("description", "")
        if isinstance(desc, list):
            desc = " ".join(desc)

        results.append({
            "_source": "Internet Archive",
            "_raw_id": ident,
            "title": str(doc.get("title", "")).strip(),
            "author": str(creator).strip(),
            "genre_raw": ["Kho lưu trữ số"],
            "year": year_int,
            "isbn": "",
            "publisher": "Internet Archive Digital Library",
            "pages": 0,
            "language": str(doc.get("language", "eng")),
            "cover_url": cover_url,
            "rating": 4.2,
            "description_raw": _strip_html(desc),
            "library_url": ia_link,
            "purchase_url": "",
            "reading_available": True,
            "reading_type": "Trực tuyến (Archive.org)",
            "reading_url": ia_link,
        })
    return results


# ---------------------------------------------------------------------------
# 5. Europeana Connector
# ---------------------------------------------------------------------------

EUROPEANA_URL = "https://api.europeana.eu/record/v2/search.json"

def search_europeana(
    query: str = "",
    author: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search Europeana cultural heritage digital library API."""
    api_key = os.getenv("EUROPEANA_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        LOGGER.info("Europeana skipped: EUROPEANA_API_KEY not configured in .env.")
        return []

    q_parts = []
    if query.strip():
        q_parts.append(query.strip())
    if author.strip():
        q_parts.append(f'who:"{author.strip()}"')
    if not q_parts:
        return []

    params = {
        "wskey": api_key,
        "query": " AND ".join(q_parts),
        "qf": "TYPE:TEXT",
        "rows": min(limit, 50),
    }

    try:
        resp = requests.get(EUROPEANA_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("Europeana request failed: %s", exc)
        return []

    results = []
    for item in data.get("items", []):
        title = item.get("title", [""])[0] if item.get("title") else ""
        creator = item.get("dcCreator", ["Không rõ tác giả"])[0] if item.get("dcCreator") else "Không rõ tác giả"
        guid = item.get("guid", "")
        edmPreview = item.get("edmPreview", [""])[0] if item.get("edmPreview") else ""
        year_raw = item.get("year", [0])[0] if item.get("year") else 0
        try:
            year_int = int(year_raw)
        except (ValueError, TypeError):
            year_int = 0

        results.append({
            "_source": "Europeana",
            "_raw_id": item.get("id", ""),
            "title": str(title).strip(),
            "author": str(creator).strip(),
            "genre_raw": ["Di sản văn hóa Châu Âu"],
            "year": year_int,
            "isbn": "",
            "publisher": "Europeana Cultural Heritage",
            "pages": 0,
            "language": "eng",
            "cover_url": edmPreview,
            "rating": 4.0,
            "description_raw": f"Tài liệu văn hóa và sách số hóa từ các thư viện quốc gia châu Âu được cung cấp bởi Europeana.",
            "library_url": guid,
            "purchase_url": "",
            "reading_available": bool(guid),
            "reading_type": "Bảo tàng/Thư viện số Châu Âu",
            "reading_url": guid,
        })
    return results


# ---------------------------------------------------------------------------
# 6. iTunes / Apple Books Connector
# ---------------------------------------------------------------------------

ITUNES_URL = "https://itunes.apple.com/search"

_ITUNES_GENRE_MAP: dict[str, str] = {
    "self improvement": "Kỹ năng sống", "self-improvement": "Kỹ năng sống",
    "business & personal finance": "Kinh doanh", "business": "Kinh doanh",
    "economics": "Kinh tế", "health, mind & body": "Sức khỏe", "health": "Sức khỏe",
    "fiction & literature": "Tiểu thuyết", "fiction": "Tiểu thuyết",
    "science & nature": "Khoa học", "science": "Khoa học", "history": "Lịch sử",
    "philosophy": "Triết học", "education": "Giáo dục", "computers & internet": "Công nghệ",
    "technology": "Công nghệ", "children": "Thiếu nhi", "biographies & memoirs": "Tiểu sử",
}


def _map_itunes_genre(genres: list[str]) -> str:
    for g in genres:
        key = g.strip().lower()
        if key in _ITUNES_GENRE_MAP:
            return _ITUNES_GENRE_MAP[key]
        for eng, vie in _ITUNES_GENRE_MAP.items():
            if eng in key:
                return vie
    return genres[0].title() if genres else "Tổng hợp"


def search_itunes_books(
    keywords: str = "",
    country: str = "vn",
    limit: int = 20,
) -> list[dict]:
    """Search iTunes/Apple Books API for commercial ebooks with preview and purchase URL."""
    if not keywords.strip():
        return []
    params = {
        "term": keywords.strip(),
        "media": "ebook",
        "country": country or "vn",
        "limit": min(limit, 100),
    }
    try:
        resp = requests.get(ITUNES_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.error("iTunes request failed: %s", exc)
        return []

    results = []
    for item in data.get("results", []):
        genres_list: list[str] = item.get("genres", [])
        cover_raw: str = item.get("artworkUrl100", "")
        cover_url = cover_raw.replace("100x100bb", "600x600bb") if cover_raw else ""
        year_raw = str(item.get("releaseDate", ""))
        year = int(year_raw[:4]) if year_raw and year_raw[:4].isdigit() else 0
        description = _strip_html(item.get("description", ""))
        track_id = item.get("trackId", "")
        results.append({
            "_source": "Apple Books",
            "_raw_id": str(track_id),
            "title": str(item.get("trackName", "")).strip(),
            "author": str(item.get("artistName", "Không rõ tác giả")).strip(),
            "genre_raw": genres_list,
            "year": year,
            "isbn": "",
            "publisher": str(item.get("sellerName", "")).strip(),
            "pages": int(item.get("pageCount", 0) or 0),
            "language": "vie" if country == "vn" else "eng",
            "cover_url": cover_url,
            "rating": float(item.get("averageUserRating", 4.0) or 4.0),
            "description_raw": description,
            "purchase_url": str(item.get("trackViewUrl", "")),
            "library_url": "",
            "reading_available": False,
            "reading_type": "",
            "reading_url": "",
        })
    return results


# ---------------------------------------------------------------------------
# Normalizer: map raw connector item into 26-column CSV record
# ---------------------------------------------------------------------------

def normalize_book_record(raw: dict, existing_df: pd.DataFrame) -> dict:
    """Map any connector raw result to the exact 26-column schema."""
    source = raw.get("_source", "Tổng hợp")
    genre_raw = raw.get("genre_raw", [])
    genre_list = genre_raw if isinstance(genre_raw, list) else [str(genre_raw)]

    if source in ("Open Library", "Google Books", "Internet Archive", "Project Gutenberg", "Europeana"):
        genre = _map_ol_genre(genre_list)
    elif source == "Apple Books":
        genre = _map_itunes_genre(genre_list)
    else:
        genre = "Tổng hợp"

    lang_code = str(raw.get("language", "vie")).lower()
    if lang_code in ("vie", "vi", "tiếng việt"):
        language = "Tiếng Việt"
    elif lang_code in ("eng", "en", "tiếng anh"):
        language = "Tiếng Anh"
    elif lang_code in ("fra", "fr"):
        language = "Tiếng Pháp"
    else:
        language = lang_code.title() if lang_code else "Tiếng Việt"

    title = str(raw.get("title", "")).strip()
    author = str(raw.get("author", "Không rõ tác giả")).strip()
    year = int(raw.get("year") or 0)

    description = raw.get("description_raw", "")
    if not description:
        description = f"Sách '{title}' của tác giả {author}" + (f", xuất bản năm {year}." if year else ".")

    summary = (description[:500] + "...") if len(description) > 500 else description

    tags = ", ".join(str(s) for s in genre_list[:4])

    # Determine reading availability and format
    reading_avail = bool(raw.get("reading_available", False))
    reading_type = str(raw.get("reading_type", ""))
    reading_url = str(raw.get("reading_url", ""))
    library_url = str(raw.get("library_url", ""))
    purchase_url = str(raw.get("purchase_url", ""))

    fmt = "Ebook" if (source in ("Apple Books", "itunes", "Project Gutenberg", "gutenberg", "Internet Archive", "internet_archive") or reading_avail) else "Bìa mềm"

    book_id = _next_book_id(existing_df)

    record: dict[str, Any] = {
        "book_id": book_id,
        "title": title,
        "author": author,
        "author_id": "",
        "genre": genre,
        "description": description,
        "year": year,
        "isbn": _clean_isbn(str(raw.get("isbn", ""))),
        "publisher": str(raw.get("publisher", "")).strip(),
        "pages": int(raw.get("pages") or 0),
        "language": language,
        "format": fmt,
        "cover_url": str(raw.get("cover_url", "")).strip(),
        "rating": min(5.0, max(0.0, float(raw.get("rating") or 4.0))),
        "featured": False,
        "tags": tags,
        "target_audience": "Mọi độc giả",
        "mood": "Muốn học hỏi",
        "difficulty": "Trung bình",
        "summary": summary,
        "reading_available": reading_avail,
        "reading_type": reading_type,
        "reading_url": reading_url,
        "local_file": "",
        "purchase_url": purchase_url,
        "library_url": library_url,
    }

    # Safeguard all 26 fields
    for field in BOOK_FIELDS:
        if field not in record:
            record[field] = FIELD_DEFAULTS.get(field, "")
    return {f: record[f] for f in BOOK_FIELDS}


# ---------------------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------------------

_DUPLICATE_STATUS = "duplicate"
_NEW_STATUS = "new"
_UNCERTAIN_STATUS = "uncertain"

def detect_duplicates(
    candidates: list[dict],
    existing_books_df: pd.DataFrame,
) -> list[dict]:
    """Classify candidates as 'new', 'duplicate', or 'uncertain'."""
    if existing_books_df.empty:
        for c in candidates:
            c["status"] = _NEW_STATUS
            c["match_reason"] = ""
        return candidates

    existing_titles = {_normalize(t): i for i, t in enumerate(existing_books_df["title"].tolist())}
    existing_title_author = {
        (_normalize(t), _normalize(a)): True
        for t, a in zip(
            existing_books_df["title"].tolist(),
            existing_books_df["author"].tolist(),
        )
    }
    existing_isbns: set[str] = set()
    if "isbn" in existing_books_df.columns:
        existing_isbns = {
            _clean_isbn(str(v))
            for v in existing_books_df["isbn"].tolist()
            if _clean_isbn(str(v))
        }

    for c in candidates:
        isbn = _clean_isbn(str(c.get("isbn", "")))
        norm_title = _normalize(c.get("title", ""))
        norm_author = _normalize(c.get("author", ""))

        if isbn and isbn in existing_isbns:
            c["status"] = _DUPLICATE_STATUS
            c["match_reason"] = f"ISBN trùng: {isbn}"
        elif (norm_title, norm_author) in existing_title_author:
            c["status"] = _DUPLICATE_STATUS
            c["match_reason"] = "Tên sách + tác giả trùng"
        elif norm_title in existing_titles:
            c["status"] = _UNCERTAIN_STATUS
            c["match_reason"] = "Tên sách trùng (tác giả khác?)"
        else:
            c["status"] = _NEW_STATUS
            c["match_reason"] = ""

    return candidates


# ---------------------------------------------------------------------------
# Save to CSV
# ---------------------------------------------------------------------------

def save_books_to_csv(
    new_books: list[dict],
    csv_path: Path = BOOKS_CSV_PATH,
) -> dict[str, int]:
    """Append confirmed new books to CSV without creating duplicates."""
    stats = {"saved": 0, "skipped": 0, "errors": 0}
    if not new_books:
        return stats

    try:
        if csv_path.exists():
            existing_df = pd.read_csv(csv_path).fillna("")
        else:
            existing_df = pd.DataFrame(columns=BOOK_FIELDS)

        existing_titles_norm = {_normalize(t) for t in existing_df["title"].tolist()}
        existing_isbns = {_clean_isbn(str(v)) for v in existing_df.get("isbn", []) if _clean_isbn(str(v))}

        to_add = []
        for book in new_books:
            title_norm = _normalize(book.get("title", ""))
            isbn_clean = _clean_isbn(str(book.get("isbn", "")))

            if title_norm in existing_titles_norm or (isbn_clean and isbn_clean in existing_isbns):
                stats["skipped"] += 1
                continue

            current_all = pd.concat([existing_df, pd.DataFrame(to_add)], ignore_index=True) if to_add else existing_df
            book["book_id"] = _next_book_id(current_all)

            for field in BOOK_FIELDS:
                if field not in book:
                    book[field] = FIELD_DEFAULTS.get(field, "")
            to_add.append({f: book.get(f, FIELD_DEFAULTS.get(f, "")) for f in BOOK_FIELDS})

            existing_titles_norm.add(title_norm)
            if isbn_clean:
                existing_isbns.add(isbn_clean)

        if not to_add:
            return stats

        new_df = pd.DataFrame(to_add, columns=BOOK_FIELDS)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        for field in BOOK_FIELDS:
            if field not in combined.columns:
                combined[field] = FIELD_DEFAULTS.get(field, "")
        combined = combined[BOOK_FIELDS]
        combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        stats["saved"] = len(to_add)

    except Exception as exc:
        LOGGER.error("CSV write failed: %s", exc)
        stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Incremental ChromaDB Upsert
# ---------------------------------------------------------------------------

def ingest_books_to_chroma(
    books_to_ingest: list[dict],
    gemini_api_key: str,
    chroma_path: Path = BASE_DIR / "chroma_db",
    max_retries: int = 3,
    progress_callback=None,
) -> dict[str, int]:
    """Upsert only specified books into existing ChromaDB collection."""
    stats = {"upserted": 0, "failed": 0}
    if not books_to_ingest:
        return stats

    try:
        import chromadb
        from google import genai
    except ImportError as exc:
        LOGGER.error("Missing dependency: %s", exc)
        stats["failed"] = len(books_to_ingest)
        return stats

    try:
        gemini_client = genai.Client(api_key=gemini_api_key)
        chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:
        LOGGER.error("ChromaDB/Gemini init failed: %s", exc)
        stats["failed"] = len(books_to_ingest)
        return stats

    total = len(books_to_ingest)
    for idx, book in enumerate(books_to_ingest):
        book_id = str(book.get("book_id", ""))
        title = str(book.get("title", ""))
        if not book_id or not title:
            stats["failed"] += 1
            continue

        doc_text = (
            f"Title: {title}\n"
            f"Author: {book.get('author', '')}\n"
            f"Genre: {book.get('genre', '')}\n"
            f"Publication year: {int(book.get('year') or 0)}\n"
            f"Tags: {book.get('tags', '')}\n"
            f"Target audience: {book.get('target_audience', '')}\n"
            f"Mood: {book.get('mood', '')}\n"
            f"Difficulty: {book.get('difficulty', '')}\n"
            f"Summary: {book.get('summary', '')}\n"
            f"Description: {book.get('description', '')}"
        )
        embedding_text = f"title: {title} | text: {doc_text}"

        last_error = None
        vector = None
        for attempt in range(max_retries):
            try:
                response = gemini_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=embedding_text,
                )
                embeddings = getattr(response, "embeddings", None)
                if embeddings and getattr(embeddings[0], "values", None):
                    vector = [float(v) for v in embeddings[0].values]
                    break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        if vector is None:
            LOGGER.error("Embedding failed for '%s': %s", title, last_error)
            stats["failed"] += 1
            if progress_callback:
                progress_callback(idx + 1, total)
            continue

        metadata = {
            "title": title,
            "author": str(book.get("author", "")),
            "genre": str(book.get("genre", "")),
            "year": int(book.get("year") or 0),
            "book_id": book_id,
            "author_id": str(book.get("author_id", "")),
            "tags": str(book.get("tags", "")),
            "target_audience": str(book.get("target_audience", "")),
            "mood": str(book.get("mood", "")),
            "difficulty": str(book.get("difficulty", "")),
            "rating": float(book.get("rating") or 4.0),
            "featured": bool(book.get("featured", False)),
        }
        try:
            collection.upsert(
                ids=[book_id],
                documents=[doc_text],
                embeddings=[vector],
                metadatas=[metadata],
            )
            stats["upserted"] += 1
        except Exception as exc:
            LOGGER.error("ChromaDB upsert failed for '%s': %s", title, exc)
            stats["failed"] += 1

        if progress_callback:
            progress_callback(idx + 1, total)

        time.sleep(1.0)

    return stats


# ---------------------------------------------------------------------------
# Multi-source Crawl and Prepare Pipeline
# ---------------------------------------------------------------------------

SOURCE_MAP = {
    "open_library": ("Open Library", search_open_library),
    "google_books": ("Google Books", search_google_books),
    "gutenberg": ("Project Gutenberg", search_project_gutenberg),
    "internet_archive": ("Internet Archive", search_internet_archive),
    "europeana": ("Europeana", search_europeana),
    "itunes": ("Apple Books", search_itunes_books),
}

def crawl_and_prepare(
    source: str,
    query: str = "",
    author: str = "",
    subject: str = "",
    isbn: str = "",
    language: str = "",
    year_from: int = 0,
    year_to: int = 0,
    limit: int = 20,
    existing_df: pd.DataFrame | None = None,
) -> list[dict]:
    """Execute search across one or all sources and return normalized duplicates."""
    if existing_df is None:
        try:
            existing_df = pd.read_csv(BOOKS_CSV_PATH).fillna("")
        except FileNotFoundError:
            existing_df = pd.DataFrame(columns=BOOK_FIELDS)

    raw_results: list[dict] = []

    if source == "all":
        # Search multiple authoritative sources in sequence with per-source error containment
        sub_limit = max(5, limit // 3)
        sources_to_call = ["open_library", "gutenberg", "internet_archive", "itunes", "google_books"]
        for src_key in sources_to_call:
            try:
                if src_key == "open_library":
                    raw_results.extend(search_open_library(query, author, subject, isbn, language, year_from, year_to, sub_limit))
                elif src_key == "google_books":
                    raw_results.extend(search_google_books(query, author, subject, isbn, language, sub_limit))
                elif src_key == "gutenberg":
                    raw_results.extend(search_project_gutenberg(query, author, subject, language, sub_limit))
                elif src_key == "internet_archive":
                    raw_results.extend(search_internet_archive(query, author, subject, sub_limit))
                elif src_key == "itunes":
                    raw_results.extend(search_itunes_books(" ".join(filter(None, [query, author, subject])), limit=sub_limit))
            except Exception as e:
                LOGGER.warning("Connector %s failed during multi-source search: %s", src_key, e)
    elif source in ("open_library", "Open Library", "openlibrary"):
        raw_results = search_open_library(query, author, subject, isbn, language, year_from, year_to, limit)
    elif source in ("google_books", "Google Books"):
        raw_results = search_google_books(query, author, subject, isbn, language, limit)
    elif source in ("gutenberg", "Project Gutenberg"):
        raw_results = search_project_gutenberg(query, author, subject, language, limit)
    elif source in ("internet_archive", "Internet Archive"):
        raw_results = search_internet_archive(query, author, subject, limit)
    elif source in ("europeana", "Europeana"):
        raw_results = search_europeana(query, author, limit)
    elif source in ("itunes", "Apple Books", "iTunes / Apple Books"):
        raw_results = search_itunes_books(" ".join(filter(None, [query, author, subject])), limit=limit)
    else:
        return []

    normalized: list[dict] = []
    running_df = existing_df.copy()
    for raw in raw_results:
        if not str(raw.get("title", "")).strip():
            continue
        record = normalize_book_record(raw, running_df)
        record["_source"] = raw.get("_source", source)
        normalized.append(record)
        running_df = pd.concat([running_df, pd.DataFrame([record])], ignore_index=True)

    classified = detect_duplicates(normalized, existing_df)
    return classified


# ---------------------------------------------------------------------------
# Recovery & Synchronization
# ---------------------------------------------------------------------------

def get_unindexed_books(
    csv_path: Path = BOOKS_CSV_PATH,
    chroma_path: Path = BASE_DIR / "chroma_db",
) -> list[dict]:
    """Find books present in CSV that do not have an embedding in ChromaDB."""
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path).fillna("")
    if df.empty or "book_id" not in df.columns:
        return []

    sqlite_file = chroma_path / "chroma.sqlite3"
    indexed_ids: set[str] = set()
    if sqlite_file.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(sqlite_file))
            cur = conn.cursor()
            cur.execute("SELECT embedding_id FROM embeddings")
            indexed_ids = {str(row[0]) for row in cur.fetchall()}
            conn.close()
        except Exception as exc:
            LOGGER.warning("Could not read ChromaDB SQLite: %s", exc)

    unindexed: list[dict] = []
    for _, row in df.iterrows():
        bid = str(row["book_id"]).strip()
        if bid and bid not in indexed_ids:
            unindexed.append(row.to_dict())

    return unindexed


def sync_unindexed_books_to_chroma(
    gemini_api_key: str,
    csv_path: Path = BOOKS_CSV_PATH,
    chroma_path: Path = BASE_DIR / "chroma_db",
    progress_callback=None,
) -> dict[str, int]:
    """Safely index unindexed books without wiping or recreating collection."""
    unindexed = get_unindexed_books(csv_path, chroma_path)
    if not unindexed:
        return {"upserted": 0, "failed": 0, "total_unindexed": 0}

    stats = ingest_books_to_chroma(
        books_to_ingest=unindexed,
        gemini_api_key=gemini_api_key,
        chroma_path=chroma_path,
        progress_callback=progress_callback,
    )
    stats["total_unindexed"] = len(unindexed)
    return stats
