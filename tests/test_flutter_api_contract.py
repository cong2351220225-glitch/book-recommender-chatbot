from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_contract_01_auth_register_and_login():
    """Verify Flutter's UserModel matches FastAPI auth responses."""
    test_user = "flutter_contract_user"
    test_pass = "pass12345"

    # Register
    res = client.post("/api/v1/auth/register", json={"username": test_user, "password": test_pass})
    assert res.status_code in [201, 400]
    if res.status_code == 201:
        data = res.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "username" in data
        assert "role" in data
        assert data["role"] == "user"

    # Login
    login_res = client.post("/api/v1/auth/login", json={"username": test_user, "password": test_pass})
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["access_token"]
    assert token is not None

    # Get Me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == test_user
    assert me_data["role"] == "user"


def test_contract_02_home_stats():
    """Verify Flutter's HomeStatsModel matches FastAPI /home/stats response."""
    res = client.get("/api/v1/home/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_books" in data
    assert data["total_books"] == 208
    assert "total_authors" in data
    assert data["total_authors"] > 0
    assert "total_genres" in data
    assert data["total_genres"] > 0
    assert "online_reading_count" in data
    assert "featured_books" in data
    assert isinstance(data["featured_books"], list)


def test_contract_03_books_catalog_pagination():
    """Verify Flutter's BookListResponse matches FastAPI /books pagination."""
    res = client.get("/api/v1/books?page=1&page_size=20&sort_by=Phù hợp")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 208
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 11
    assert len(data["items"]) == 20

    # Verify BookModel has all 26 fields expected by Flutter
    first_book = data["items"][0]
    expected_fields = [
        "book_id", "title", "author", "author_id", "genre", "description",
        "year", "isbn", "publisher", "pages", "language", "format",
        "cover_url", "rating", "featured", "tags", "target_audience",
        "mood", "difficulty", "summary", "reading_available", "reading_type",
        "reading_url", "local_file", "purchase_url", "library_url",
    ]
    for field in expected_fields:
        assert field in first_book, f"Missing field in BookModel: {field}"


def test_contract_04_book_search_and_filters():
    """Verify search parameters used by Flutter (q, title, author, isbn, genre)."""
    # 4a. Title search
    res_title = client.get("/api/v1/books?title=Pragmatic")
    assert res_title.status_code == 200
    assert any("Pragmatic" in b["title"] for b in res_title.json()["items"])

    # 4b. Author search
    res_author = client.get("/api/v1/books?author=Andy Hunt")
    assert res_author.status_code == 200
    assert any("Andy Hunt" in b["author"] for b in res_author.json()["items"])

    # 4c. ISBN search
    res_isbn = client.get("/api/v1/books?isbn=0132100673")
    assert res_isbn.status_code == 200
    assert any(b["book_id"] == "book_203" for b in res_isbn.json()["items"])


def test_contract_05_book_detail_and_related():
    """Verify Flutter's BookDetailResponse and related books."""
    res = client.get("/api/v1/books/book_208")
    assert res.status_code == 200
    data = res.json()
    assert "book" in data
    assert data["book"]["book_id"] == "book_208"
    assert "related_books" in data
    assert "reading_status" in data
    assert "can_read" in data

    # Related books endpoint
    res_rel = client.get("/api/v1/books/book_208/related?limit=5")
    assert res_rel.status_code == 200
    assert isinstance(res_rel.json(), list)


def test_contract_06_authors_list_and_detail():
    """Verify Flutter's AuthorModel and AuthorDetailResponse."""
    # List
    res = client.get("/api/v1/authors")
    assert res.status_code == 200
    authors = res.json()
    assert len(authors) > 0
    first_author = authors[0]
    assert "author_id" in first_author
    assert "name" in first_author
    assert "work_count" in first_author
    assert "genres" in first_author

    # Detail
    author_id = first_author["author_id"]
    res_detail = client.get(f"/api/v1/authors/{author_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "author" in detail_data
    assert "books" in detail_data
    assert isinstance(detail_data["books"], list)


def test_contract_07_genres_list():
    """Verify Flutter's GenreModel matches FastAPI /genres."""
    res = client.get("/api/v1/genres")
    assert res.status_code == 200
    genres = res.json()
    assert len(genres) >= 16
    for g in genres:
        assert "genre_id" in g
        assert "name" in g
        assert "book_count" in g


def test_contract_08_error_codes_handling():
    """Verify error status codes expected by Flutter's ApiException."""
    # 401 Unauthorized
    res_401 = client.get("/api/v1/auth/me")
    assert res_401.status_code == 401
    assert "detail" in res_401.json()

    # 404 Not Found
    res_404 = client.get("/api/v1/books/book_invalid_999999")
    assert res_404.status_code == 404
    assert "detail" in res_404.json()

    # 400 Bad Request
    res_400 = client.post("/api/v1/auth/register", json={"username": "ab", "password": "12"})
    assert res_400.status_code == 422 or res_400.status_code == 400


def test_contract_09_bookshelf_api_contract():
    """Verify Flutter's BookshelfItemModel matches FastAPI /bookshelf response."""
    from backend.core.security import create_access_token

    token = create_access_token(data={"sub": "contract_tester", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    # Add item
    add_res = client.post(
        "/api/v1/bookshelf",
        headers=headers,
        json={"book_id": "book_203", "status": "favorite", "progress_page": 20, "notes": "Hợp đồng Flutter"},
    )
    assert add_res.status_code in [201, 400]
    if add_res.status_code == 201:
        data = add_res.json()
        assert "id" in data
        assert "book_id" in data
        assert "status" in data
        assert "progress_page" in data
        assert "total_pages" in data
        assert "rating" in data
        assert "notes" in data
        assert "added_at" in data
        assert "updated_at" in data
        assert "book" in data
        assert data["book"]["book_id"] == "book_203"
        assert data["book"]["title"] == "The Pragmatic Programmer"

    # List items
    list_res = client.get("/api/v1/bookshelf", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert "total" in list_data
    assert "items" in list_data
    assert len(list_data["items"]) >= 1

    # Check book
    check_res = client.get("/api/v1/bookshelf/check/book_203", headers=headers)
    assert check_res.status_code == 200
    check_data = check_res.json()
    assert check_data["in_bookshelf"] is True
    assert "favorite" in check_data["statuses"]


def test_contract_10_reading_api_contract():
    """Verify Flutter's ReadingDocInfoModel and ReadingProgressModel match FastAPI responses."""
    from backend.core.security import create_access_token

    token = create_access_token(data={"sub": "contract_reader", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Reading Document Info
    info_res = client.get("/api/v1/reading/info/book_203", headers=headers)
    assert info_res.status_code == 200
    info_data = info_res.json()
    assert "book_id" in info_data
    assert "title" in info_data
    assert "can_read" in info_data
    assert "format" in info_data
    assert "file_size_bytes" in info_data
    assert "file_url" in info_data

    # 2. Reading Progress Save
    prog_res = client.post(
        "/api/v1/reading/progress",
        headers=headers,
        json={"book_id": "book_203", "current_page": 2, "total_pages": 5, "last_read_location": "Trang 2"},
    )
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert "book_id" in prog_data
    assert "current_page" in prog_data
    assert "total_pages" in prog_data
    assert "progress_percent" in prog_data
    assert "last_read_location" in prog_data
    assert "updated_at" in prog_data
    assert prog_data["current_page"] == 2
    assert prog_data["total_pages"] == 5


def test_contract_11_crawler_admin_contract():
    """Verify Flutter's Crawler models match FastAPI crawler responses."""
    from backend.core.security import create_access_token

    admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Sources contract
    sources_res = client.get("/api/v1/crawler/sources")
    assert sources_res.status_code == 200
    sources_data = sources_res.json()
    assert "sources" in sources_data
    for src in sources_data["sources"]:
        assert "id" in src
        assert "name" in src
        assert "description" in src

    # 2. Search contract
    search_res = client.post(
        "/api/v1/crawler/search",
        json={"query": "machine learning", "source": "openlibrary", "limit": 2},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "query" in search_data
    assert "source" in search_data
    assert "total_found" in search_data
    assert "results" in search_data

    # 3. Batch import contract (with admin token, using duplicate book Atomic Habits to keep real books.csv unmodified)
    batch_res = client.post(
        "/api/v1/crawler/batch-import",
        headers=admin_headers,
        json={
            "candidates": [
                {"title": "Atomic Habits", "author": "James Clear", "isbn": ""}
            ],
            "upsert_chroma": False,
        },
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert "total_requested" in batch_data
    assert "imported_count" in batch_data
    assert "skipped_count" in batch_data
    assert "results" in batch_data
    for item in batch_data["results"]:
        assert "title" in item
        assert "success" in item
        assert "message" in item
        assert "vector_indexed" in item


def test_contract_12_recommendations_contract():
    """Verify Flutter's Recommendation models match FastAPI recommendation endpoints."""
    from backend.core.security import create_access_token

    user_token = create_access_token(data={"sub": "flutter_rec_contract_user", "role": "user"})
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. For You
    res_for_you = client.get("/api/v1/recommendations/for-you?limit=3", headers=headers)
    assert res_for_you.status_code == 200
    data_for_you = res_for_you.json()
    assert "total" in data_for_you
    assert "recommendations" in data_for_you
    assert "algorithm" in data_for_you
    assert "is_personalized" in data_for_you
    assert "source_basis" in data_for_you

    # 2. Preferences
    res_pref = client.get("/api/v1/recommendations/preferences", headers=headers)
    assert res_pref.status_code == 200
    data_pref = res_pref.json()
    assert "username" in data_pref
    assert "preferred_genres" in data_pref

    # 3. Similar
    res_similar = client.get("/api/v1/recommendations/similar/book_001?limit=2")
    assert res_similar.status_code == 200
    assert len(res_similar.json()["recommendations"]) > 0


