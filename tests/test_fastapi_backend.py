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
from backend.core.database import get_books_df, load_users, save_users

client = TestClient(app)


# -------------------------------------------------------------
# 1. Total books count verification (exact 208 books)
# -------------------------------------------------------------
def test_01_total_books_count_208():
    response = client.get("/api/v1/books?page=1&page_size=10")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["total"] == 208, f"Expected total 208 books, got {data['total']}"
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] == 21


# -------------------------------------------------------------
# 2. Search by title, author, and ISBN
# -------------------------------------------------------------
def test_02_search_books():
    # 2a. Search by title
    res_title = client.get("/api/v1/books?title=Pragmatic")
    assert res_title.status_code == 200
    items_title = res_title.json()["items"]
    assert any("Pragmatic" in b["title"] for b in items_title)

    # 2b. Search by author
    res_author = client.get("/api/v1/books?author=Andy Hunt")
    assert res_author.status_code == 200
    items_author = res_author.json()["items"]
    assert any("Andy Hunt" in b["author"] for b in items_author)

    # 2c. Search by ISBN: The Pragmatic Programmer has ISBN 020161622X / 9780201616224 or 0132100673
    # Let's search by book_203's isbn
    books_df = get_books_df()
    b203 = books_df[books_df["book_id"] == "book_203"]
    assert not b203.empty
    isbn_val = str(b203.iloc[0]["isbn"])
    if isbn_val:
        res_isbn = client.get(f"/api/v1/books?isbn={isbn_val}")
        assert res_isbn.status_code == 200
        items_isbn = res_isbn.json()["items"]
        assert any(b["book_id"] == "book_203" for b in items_isbn)


# -------------------------------------------------------------
# 3. Book detail and related books (book_208)
# -------------------------------------------------------------
def test_03_book_detail_and_related():
    # Detail for book_208
    res = client.get("/api/v1/books/book_208")
    assert res.status_code == 200
    detail = res.json()
    assert detail["book"]["book_id"] == "book_208"
    assert "title" in detail["book"]
    assert "reading_status" in detail

    # Related books
    res_rel = client.get("/api/v1/books/book_208/related")
    assert res_rel.status_code == 200
    rel_books = res_rel.json()
    assert isinstance(rel_books, list)

    # 404 for nonexistent book
    res_404 = client.get("/api/v1/books/book_999999")
    assert res_404.status_code == 404


# -------------------------------------------------------------
# 4. Register, Login, JWT auth token validation
# -------------------------------------------------------------
def test_04_auth_register_and_login_jwt():
    test_user = "test_user_phase1"
    test_pass = "secret12345"

    # Clean up prior test user if exists
    users = load_users()
    if test_user in users:
        del users[test_user]
        save_users(users)

    # Register
    reg_res = client.post("/api/v1/auth/register", json={"username": test_user, "password": test_pass})
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["username"] == test_user
    assert reg_data["role"] == "user"

    # Cannot register duplicate
    dup_res = client.post("/api/v1/auth/register", json={"username": test_user, "password": test_pass})
    assert dup_res.status_code == 400

    # Login
    login_res = client.post("/api/v1/auth/login", json={"username": test_user, "password": test_pass})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify profile via /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == test_user
    assert me_res.json()["role"] == "user"

    # Clean up
    users = load_users()
    if test_user in users:
        del users[test_user]
        save_users(users)


# -------------------------------------------------------------
# 5. Role-based Access Control (Admin vs Normal User)
# -------------------------------------------------------------
def test_05_admin_rbac():
    # 5a. Admin login (cong1 / 123)
    admin_login = client.post("/api/v1/auth/login", json={"username": "cong1", "password": "123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    assert admin_login.json()["role"] == "admin"

    # Admin can access unindexed crawler status
    admin_res = client.get("/api/v1/crawler/unindexed", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200
    assert "unindexed_books" in admin_res.json()

    # 5b. Regular user attempting admin action
    reg_user = "normal_user_phase1"
    reg_pass = "userpass123"
    users = load_users()
    users[reg_user] = {"password": reg_pass, "role": "user"}
    save_users(users)

    user_login = client.post("/api/v1/auth/login", json={"username": reg_user, "password": reg_pass})
    user_token = user_login.json()["access_token"]

    # Regular user attempting admin endpoints should receive 403 Forbidden
    forbidden_res1 = client.get("/api/v1/crawler/unindexed", headers={"Authorization": f"Bearer {user_token}"})
    assert forbidden_res1.status_code == 403

    forbidden_res2 = client.post(
        "/api/v1/crawler/import",
        json={"candidate": {"title": "Test Book"}, "upsert_chroma": False},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert forbidden_res2.status_code == 403

    # Clean up
    users = load_users()
    if reg_user in users:
        del users[reg_user]
        save_users(users)


# -------------------------------------------------------------
# 6. Chat RAG retrieval from existing ChromaDB
# -------------------------------------------------------------
def test_06_rag_chat_retrieval():
    # Library info question
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Thư viện hiện có bao nhiêu cuốn sách?", "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "208" in data["answer"]
    assert data["intent"] in ["library_info", "book_query"]


# -------------------------------------------------------------
# 7. Anti-hallucination / Out of Domain Handling
# -------------------------------------------------------------
def test_07_anti_hallucination_out_of_domain():
    # Out of domain query
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Thời tiết ngày mai ở thành phố Paris thế nào?", "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    # Chatbot correctly handles out of domain without hallucinating library books
    assert data["intent"] == "out_of_domain" or len(data["books"]) == 0


# -------------------------------------------------------------
# 8. Crawler search and source handling
# -------------------------------------------------------------
def test_08_crawler_sources_and_search():
    # Sources list
    sources_res = client.get("/api/v1/crawler/sources")
    assert sources_res.status_code == 200
    sources = sources_res.json()["sources"]
    assert len(sources) >= 6
    source_ids = [s["id"] for s in sources]
    assert "openlibrary" in source_ids
    assert "google_books" in source_ids
    assert "gutenberg" in source_ids


# -------------------------------------------------------------
# 9. Unauthorized request rejection (401/403)
# -------------------------------------------------------------
def test_09_unauthorized_rejection():
    # No auth header for /me
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 401

    # Invalid token
    res_invalid = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res_invalid.status_code == 401

    # Crawler import without auth
    res_import = client.post("/api/v1/crawler/import", json={"candidate": {"title": "Sample"}})
    assert res_import.status_code == 401


# -------------------------------------------------------------
# 10. Health check and persistence verification
# -------------------------------------------------------------
def test_10_health_and_stats():
    # /health
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["total_books_csv"] == 208
    assert health_data["chromadb_vectors"] == 208

    # /api/v1/home/stats
    stats_res = client.get("/api/v1/home/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_books"] == 208
    assert stats["total_authors"] > 0
    assert stats["total_genres"] > 0
    assert "online_reading_count" in stats

    # /api/v1/genres
    genres_res = client.get("/api/v1/genres")
    assert genres_res.status_code == 200
    assert len(genres_res.json()) > 0

    # /api/v1/reading/status/book_001
    reading_res = client.get("/api/v1/reading/status/book_001")
    assert reading_res.status_code == 200
    assert "reading_available" in reading_res.json()
