"""Unit tests for crawler_service.py.

All network calls are mocked — no real HTTP requests are made.
Run with: .venv\Scripts\python.exe -m pytest tests/test_crawler_service.py -v
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

# Ensure project root is on path (pytest usually handles this, but be explicit)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler_service import (
    BOOK_FIELDS,
    _normalize,
    crawl_and_prepare,
    detect_duplicates,
    normalize_book_record,
    save_books_to_csv,
    search_europeana,
    search_google_books,
    search_internet_archive,
    search_itunes_books,
    search_open_library,
    search_project_gutenberg,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────

EXISTING_DF = pd.DataFrame([
    {
        "book_id": "book_001",
        "title": "Atomic Habits",
        "author": "James Clear",
        "isbn": "9780735211292",
        "genre": "Kỹ năng sống",
        "description": "Build good habits.",
        "year": 2018,
    }
])

OL_RESPONSE = {
    "docs": [
        {
            "key": "/works/OL1234W",
            "title": "Deep Work",
            "author_name": ["Cal Newport"],
            "isbn": ["9781455586691"],
            "first_publish_year": 2016,
            "subject": ["Productivity", "Self-help"],
            "language": ["eng"],
            "number_of_pages_median": 296,
            "cover_i": 12345,
            "publisher": ["Grand Central Publishing"],
            "ratings_average": 4.3,
        },
        # Duplicate of Atomic Habits
        {
            "key": "/works/OL9999W",
            "title": "Atomic Habits",
            "author_name": ["James Clear"],
            "isbn": ["9780735211292"],
            "first_publish_year": 2018,
            "subject": ["Habits"],
            "language": ["eng"],
            "number_of_pages_median": 320,
            "cover_i": None,
            "publisher": [],
            "ratings_average": 4.8,
        },
    ]
}

ITUNES_RESPONSE = {
    "results": [
        {
            "trackId": 9001,
            "trackName": "The Lean Startup",
            "artistName": "Eric Ries",
            "description": "<p>A great entrepreneurship book.</p>",
            "genres": ["Business & Personal Finance"],
            "releaseDate": "2011-09-13T07:00:00Z",
            "averageUserRating": 4.5,
            "artworkUrl100": "https://example.com/100x100bb.jpg",
            "trackViewUrl": "https://books.apple.com/lean-startup",
            "sellerName": "Crown Business",
        }
    ]
}


# ─── _normalize tests ───────────────────────────────────────────────────────

def test_normalize_strips_accents():
    assert _normalize("Tâm Lý") == "tam ly"


def test_normalize_replaces_d_with_d():
    assert _normalize("Đọc sách") == "doc sach"


def test_normalize_empty():
    assert _normalize("") == ""
    assert _normalize(None) == ""


# ─── Open Library search tests ─────────────────────────────────────────────

class _FakeOLResponse:
    status_code = 200
    def raise_for_status(self): pass
    def json(self): return OL_RESPONSE


@patch("crawler_service.requests.get", return_value=_FakeOLResponse())
def test_search_open_library_returns_list(mock_get):
    results = search_open_library(query="Deep Work", limit=10)
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["title"] == "Deep Work"
    assert results[0]["_source"] in ("Open Library", "open_library")
    assert "covers.openlibrary.org" in results[0]["cover_url"]


@patch("crawler_service.requests.get", side_effect=requests.RequestException("network error"))
def test_search_open_library_network_error_returns_empty(mock_get):
    results = search_open_library(query="whatever")
    assert results == []


# ─── iTunes search tests ───────────────────────────────────────────────────

class _FakeITResponse:
    status_code = 200
    def raise_for_status(self): pass
    def json(self): return ITUNES_RESPONSE


@patch("crawler_service.requests.get", return_value=_FakeITResponse())
def test_search_itunes_returns_list(mock_get):
    results = search_itunes_books(keywords="lean startup", limit=10)
    assert len(results) == 1
    r = results[0]
    assert r["title"] == "The Lean Startup"
    assert r["_source"] in ("Apple Books", "itunes")
    assert "600x600bb" in r["cover_url"]  # upscaled artwork
    assert r["year"] == 2011
    assert r["description_raw"] == "A great entrepreneurship book."  # HTML stripped


@patch("crawler_service.requests.get", return_value=_FakeITResponse())
def test_search_itunes_empty_keywords_returns_empty(mock_get):
    results = search_itunes_books(keywords="")
    assert results == []


# ─── normalize_book_record tests ──────────────────────────────────────────

def _make_raw_ol(title: str = "Test Book", author: str = "Test Author") -> dict:
    return {
        "_source": "open_library",
        "_raw_id": "/works/OL1W",
        "title": title,
        "author": author,
        "genre_raw": ["Fiction"],
        "year": 2020,
        "isbn": "123456789",
        "publisher": "Some Publisher",
        "pages": 200,
        "language": "eng",
        "cover_url": "https://covers.openlibrary.org/b/id/999-M.jpg",
        "rating": 4.2,
        "library_url": "https://openlibrary.org/works/OL1W",
    }


def test_normalize_book_record_has_all_fields():
    raw = _make_raw_ol()
    empty_df = pd.DataFrame(columns=BOOK_FIELDS)
    record = normalize_book_record(raw, empty_df)
    for field in BOOK_FIELDS:
        assert field in record, f"Missing field: {field}"


def test_normalize_book_record_title_author_preserved():
    raw = _make_raw_ol("My Book", "My Author")
    empty_df = pd.DataFrame(columns=BOOK_FIELDS)
    record = normalize_book_record(raw, empty_df)
    assert record["title"] == "My Book"
    assert record["author"] == "My Author"


def test_normalize_book_record_language_mapping():
    raw = _make_raw_ol()
    raw["language"] = "vie"
    empty_df = pd.DataFrame(columns=BOOK_FIELDS)
    record = normalize_book_record(raw, empty_df)
    assert record["language"] == "Tiếng Việt"

    raw2 = _make_raw_ol()
    raw2["language"] = "eng"
    record2 = normalize_book_record(raw2, empty_df)
    assert record2["language"] == "Tiếng Anh"


def test_normalize_book_record_itunes():
    raw = {
        "_source": "itunes",
        "_raw_id": "9001",
        "title": "Lean Startup",
        "author": "Eric Ries",
        "genre_raw": ["Business & Personal Finance"],
        "year": 2011,
        "isbn": "",
        "publisher": "Crown",
        "pages": 0,
        "language": "vie",
        "cover_url": "https://example.com/600x600bb.jpg",
        "rating": 4.5,
        "description_raw": "Great book",
        "purchase_url": "https://books.apple.com/lean",
    }
    empty_df = pd.DataFrame(columns=BOOK_FIELDS)
    record = normalize_book_record(raw, empty_df)
    assert record["format"] == "Ebook"
    assert record["purchase_url"] == "https://books.apple.com/lean"
    assert record["description"] == "Great book"
    for field in BOOK_FIELDS:
        assert field in record


def test_normalize_book_record_unique_book_ids():
    """Each normalized record should get a unique book_id."""
    raw1 = _make_raw_ol("Book A")
    raw2 = _make_raw_ol("Book B")
    empty_df = pd.DataFrame(columns=BOOK_FIELDS)
    rec1 = normalize_book_record(raw1, empty_df)
    # Pass rec1 as "existing" so rec2 gets a different id
    df_with_rec1 = pd.DataFrame([rec1])
    rec2 = normalize_book_record(raw2, df_with_rec1)
    assert rec1["book_id"] != rec2["book_id"]


# ─── detect_duplicates tests ──────────────────────────────────────────────

def test_detect_duplicates_isbn_match():
    candidates = [normalize_book_record(_make_raw_ol("Atomic Habits"), EXISTING_DF)]
    candidates[0]["isbn"] = "9780735211292"
    result = detect_duplicates(candidates, EXISTING_DF)
    assert result[0]["status"] == "duplicate"
    assert "ISBN" in result[0]["match_reason"]


def test_detect_duplicates_title_author_match():
    raw = _make_raw_ol("Atomic Habits", "James Clear")
    raw["isbn"] = ""  # no ISBN match
    candidates = [normalize_book_record(raw, EXISTING_DF)]
    result = detect_duplicates(candidates, EXISTING_DF)
    assert result[0]["status"] == "duplicate"


def test_detect_duplicates_title_only_uncertain():
    raw = _make_raw_ol("Atomic Habits", "Different Author")
    raw["isbn"] = ""
    candidates = [normalize_book_record(raw, EXISTING_DF)]
    result = detect_duplicates(candidates, EXISTING_DF)
    assert result[0]["status"] == "uncertain"


def test_detect_duplicates_new_book():
    raw = _make_raw_ol("A Completely New Book", "New Author")
    raw["isbn"] = ""
    candidates = [normalize_book_record(raw, EXISTING_DF)]
    result = detect_duplicates(candidates, EXISTING_DF)
    assert result[0]["status"] == "new"
    assert result[0]["match_reason"] == ""


def test_detect_duplicates_empty_existing():
    raw = _make_raw_ol("Any Book", "Any Author")
    candidates = [normalize_book_record(raw, pd.DataFrame(columns=BOOK_FIELDS))]
    result = detect_duplicates(candidates, pd.DataFrame(columns=BOOK_FIELDS))
    assert result[0]["status"] == "new"


# ─── save_books_to_csv tests ───────────────────────────────────────────────

def test_save_books_to_csv_appends_new(tmp_path):
    # Write a seed CSV
    seed = EXISTING_DF.copy()
    for field in BOOK_FIELDS:
        if field not in seed.columns:
            seed[field] = ""
    seed = seed[BOOK_FIELDS]
    csv_path = tmp_path / "books.csv"
    seed.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # One new book to add
    new_books = [{
        "book_id": "book_002",
        "title": "Deep Work",
        "author": "Cal Newport",
        "author_id": "",
        "genre": "Kỹ năng sống",
        "description": "Focus without distraction.",
        "year": 2016,
        "isbn": "9781455586691",
        "publisher": "Grand Central",
        "pages": 296,
        "language": "Tiếng Anh",
        "format": "Bìa mềm",
        "cover_url": "",
        "rating": 4.3,
        "featured": False,
        "tags": "",
        "target_audience": "Mọi độc giả",
        "mood": "Muốn học hỏi",
        "difficulty": "Trung bình",
        "summary": "Focus without distraction.",
        "reading_available": False,
        "reading_type": "",
        "reading_url": "",
        "local_file": "",
        "purchase_url": "",
        "library_url": "https://openlibrary.org/works/OL1W",
    }]
    stats = save_books_to_csv(new_books, csv_path)
    assert stats["saved"] == 1
    assert stats["skipped"] == 0
    assert stats["errors"] == 0

    result_df = pd.read_csv(csv_path)
    assert len(result_df) == 2
    assert "Deep Work" in result_df["title"].values


def test_save_books_to_csv_skips_duplicates(tmp_path):
    seed = EXISTING_DF.copy()
    for field in BOOK_FIELDS:
        if field not in seed.columns:
            seed[field] = ""
    seed = seed[BOOK_FIELDS]
    csv_path = tmp_path / "books.csv"
    seed.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Attempt to add Atomic Habits again (same title)
    dup_book = {
        "book_id": "book_dup",
        "title": "Atomic Habits",  # same title as existing
        "author": "James Clear",
        "author_id": "",
        "genre": "Kỹ năng sống",
        "description": "Duplicate.",
        "year": 2018,
        "isbn": "",
        "publisher": "",
        "pages": 0,
        "language": "Tiếng Việt",
        "format": "Bìa mềm",
        "cover_url": "",
        "rating": 4.0,
        "featured": False,
        "tags": "",
        "target_audience": "",
        "mood": "",
        "difficulty": "",
        "summary": "",
        "reading_available": False,
        "reading_type": "",
        "reading_url": "",
        "local_file": "",
        "purchase_url": "",
        "library_url": "",
    }
    stats = save_books_to_csv([dup_book], csv_path)
    assert stats["saved"] == 0
    assert stats["skipped"] == 1

    result_df = pd.read_csv(csv_path)
    assert len(result_df) == 1  # still only 1 book


def test_save_books_to_csv_empty_input(tmp_path):
    csv_path = tmp_path / "books.csv"
    stats = save_books_to_csv([], csv_path)
    assert stats["saved"] == 0
    assert stats["errors"] == 0


# ─── crawl_and_prepare integration test (mocked) ──────────────────────────

@patch("crawler_service.requests.get", return_value=_FakeOLResponse())
def test_crawl_and_prepare_open_library(mock_get):
    results = crawl_and_prepare(
        source="open_library",
        query="Deep Work",
        existing_df=EXISTING_DF,
    )
    # 2 docs returned: one new (Deep Work), one duplicate (Atomic Habits)
    assert len(results) == 2
    statuses = {r["title"]: r["status"] for r in results}
    assert statuses.get("Deep Work") == "new"
    assert statuses.get("Atomic Habits") in ("duplicate", "uncertain")


@patch("crawler_service.requests.get", return_value=_FakeITResponse())
def test_crawl_and_prepare_itunes(mock_get):
    results = crawl_and_prepare(
        source="itunes",
        query="lean startup",
        existing_df=EXISTING_DF,
    )
    assert len(results) == 1
    assert results[0]["status"] == "new"
    assert results[0]["title"] == "The Lean Startup"


def test_crawl_and_prepare_unknown_source():
    results = crawl_and_prepare(source="unknown_source", query="anything")
    assert results == []


# ─── New Connectors Tests (Mocked) ─────────────────────────────────────────

def test_search_google_books_mock():
    fake_gb_resp = MagicMock()
    fake_gb_resp.status_code = 200
    fake_gb_resp.json.return_value = {
        "items": [
            {
                "id": "gb_001",
                "volumeInfo": {
                    "title": "Clean Architecture",
                    "authors": ["Robert C. Martin"],
                    "publisher": "Prentice Hall",
                    "publishedDate": "2017-09-20",
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780134494166"}],
                    "categories": ["Computers"],
                    "pageCount": 432,
                    "language": "en",
                    "imageLinks": {"thumbnail": "http://books.google.com/thumbnail.jpg"},
                    "infoLink": "https://books.google.com/info",
                },
                "accessInfo": {
                    "webReaderLink": "https://books.google.com/reader",
                    "viewability": "PARTIAL",
                },
                "saleInfo": {"buyLink": "https://books.google.com/buy"},
            }
        ]
    }
    with patch("crawler_service.requests.get", return_value=fake_gb_resp):
        res = search_google_books(query="Clean Architecture", limit=5)
        assert len(res) == 1
        book = res[0]
        assert book["title"] == "Clean Architecture"
        assert book["author"] == "Robert C. Martin"
        assert book["isbn"] == "9780134494166"
        assert book["year"] == 2017
        assert book["_source"] == "Google Books"
        assert book["cover_url"].startswith("https://")


def test_search_google_books_rate_limit_handled():
    fake_429 = MagicMock()
    fake_429.status_code = 429
    with patch("crawler_service.requests.get", return_value=fake_429):
        res = search_google_books(query="Clean Code")
        assert res == []


def test_search_project_gutenberg_mock():
    fake_gut_resp = MagicMock()
    fake_gut_resp.status_code = 200
    fake_gut_resp.json.return_value = {
        "results": [
            {
                "id": 1342,
                "title": "Pride and Prejudice",
                "authors": [{"name": "Austen, Jane"}],
                "subjects": ["Sisters -- Fiction", "Courtship -- Fiction"],
                "languages": ["en"],
                "formats": {
                    "text/html": "https://www.gutenberg.org/files/1342/1342-h/1342-h.htm",
                    "image/jpeg": "https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg",
                },
            }
        ]
    }
    with patch("crawler_service.requests.get", return_value=fake_gut_resp):
        res = search_project_gutenberg(query="Pride and Prejudice", limit=5)
        assert len(res) == 1
        book = res[0]
        assert book["title"] == "Pride and Prejudice"
        assert book["reading_available"] is True
        assert "gutenberg.org" in book["reading_url"]
        assert book["_source"] == "Project Gutenberg"


def test_search_internet_archive_mock():
    fake_ia_resp = MagicMock()
    fake_ia_resp.status_code = 200
    fake_ia_resp.json.return_value = {
        "response": {
            "docs": [
                {
                    "identifier": "computernetworks00tane",
                    "title": "Computer networks",
                    "creator": "Tanenbaum, Andrew S.",
                    "year": 1996,
                    "description": "Textbook on computer networking.",
                    "language": "eng",
                }
            ]
        }
    }
    with patch("crawler_service.requests.get", return_value=fake_ia_resp):
        res = search_internet_archive(query="Computer networks", limit=5)
        assert len(res) == 1
        book = res[0]
        assert book["title"] == "Computer networks"
        assert book["author"] == "Tanenbaum, Andrew S."
        assert book["year"] == 1996
        assert "archive.org/details/" in book["library_url"]
        assert book["_source"] == "Internet Archive"


def test_search_europeana_no_api_key_skips_gracefully():
    with patch.dict("os.environ", {"EUROPEANA_API_KEY": ""}):
        res = search_europeana(query="Renaissance art")
        assert res == []


def test_search_europeana_mock_with_api_key():
    fake_eur_resp = MagicMock()
    fake_eur_resp.status_code = 200
    fake_eur_resp.json.return_value = {
        "items": [
            {
                "id": "eur_001",
                "title": ["Histoire de France"],
                "dcCreator": ["Michelet, Jules"],
                "guid": "https://www.europeana.eu/item/eur_001",
                "edmPreview": ["https://preview.europeana.eu/img.jpg"],
                "year": [1840],
            }
        ]
    }
    with patch.dict("os.environ", {"EUROPEANA_API_KEY": "valid_test_key"}), \
         patch("crawler_service.requests.get", return_value=fake_eur_resp):
        res = search_europeana(query="Histoire de France")
        assert len(res) == 1
        book = res[0]
        assert book["title"] == "Histoire de France"
        assert book["author"] == "Michelet, Jules"
        assert book["year"] == 1840
        assert book["_source"] == "Europeana"


def test_crawl_and_prepare_all_sources():
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"docs": [], "items": [], "results": []}
    with patch("crawler_service.requests.get", return_value=fake_resp):
        res = crawl_and_prepare(source="all", query="technology", existing_df=EXISTING_DF)
        assert isinstance(res, list)
