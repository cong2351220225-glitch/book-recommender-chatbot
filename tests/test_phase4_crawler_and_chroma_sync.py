import copy
import json
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import pandas as pd
from unittest.mock import MagicMock, patch

from backend.main import app
from backend.core.security import create_access_token
from backend.schemas.crawler_schema import (
    CrawlSearchRequest,
    CrawlBatchImportRequest,
    CrawlImportRequest,
    SyncChromaResponse,
)
from crawler_service import (
    BOOK_FIELDS,
    detect_duplicates,
    get_unindexed_books,
    sync_unindexed_books_to_chroma,
    ingest_books_to_chroma,
)
from rag_engine import handle_user_message

client = TestClient(app)

ADMIN_USER = {"username": "admin", "role": "admin", "full_name": "Library Administrator"}
NORMAL_USER = {"username": "reader_user", "role": "user", "full_name": "Test Reader"}

admin_token = create_access_token(data={"sub": ADMIN_USER["username"], "role": ADMIN_USER["role"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}

user_token = create_access_token(data={"sub": NORMAL_USER["username"], "role": NORMAL_USER["role"]})
user_headers = {"Authorization": f"Bearer {user_token}"}


# ============================================================================
# PHẦN 1: CRAWLER SEARCH, FILTER & DEDUPLICATION TESTS
# ============================================================================

def test_01_crawler_search_empty_filters_validation():
    """Tìm kiếm không có tiêu chí nào phải báo lỗi 400 Bad Request."""
    resp = client.post(
        "/api/v1/crawler/search",
        json={"query": "", "author": "", "subject": "", "isbn": ""},
    )
    assert resp.status_code == 400
    assert "Vui lòng nhập ít nhất một từ khóa" in resp.json()["detail"]


def test_02_crawler_search_by_author_only(monkeypatch):
    """Tìm kiếm chỉ bằng tên tác giả (query rỗng) phải hợp lệ và chuyển đúng tham số."""
    def fake_crawl(source, query, author, subject, isbn, language, year_from, year_to, limit, existing_df):
        assert author == "Nguyễn Nhật Ánh"
        assert query == ""
        return [
            {
                "title": "Cho tôi xin một vé đi tuổi thơ",
                "author": "Nguyễn Nhật Ánh",
                "year": 2008,
                "status": "new",
                "match_reason": "",
            }
        ]

    monkeypatch.setattr("backend.routers.crawler_router.crawl_and_prepare", fake_crawl)

    resp = client.post(
        "/api/v1/crawler/search",
        json={"author": "Nguyễn Nhật Ánh", "source": "all", "limit": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_found"] == 1
    assert data["results"][0]["author"] == "Nguyễn Nhật Ánh"


def test_03_crawler_search_by_isbn_only(monkeypatch):
    """Tìm kiếm bằng mã ISBN duy nhất."""
    def fake_crawl(source, query, author, subject, isbn, language, year_from, year_to, limit, existing_df):
        assert isbn == "9786042000000"
        return [
            {
                "title": "Sách Tìm Theo ISBN",
                "author": "Tác giả",
                "isbn": "9786042000000",
                "status": "new",
                "match_reason": "",
            }
        ]

    monkeypatch.setattr("backend.routers.crawler_router.crawl_and_prepare", fake_crawl)

    resp = client.post(
        "/api/v1/crawler/search",
        json={"isbn": "9786042000000", "source": "openlibrary"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_found"] == 1
    assert data["results"][0]["isbn"] == "9786042000000"


def test_04_crawler_search_with_year_and_language_filters(monkeypatch):
    """Tìm kiếm kết hợp lọc năm và ngôn ngữ."""
    def fake_crawl(source, query, author, subject, isbn, language, year_from, year_to, limit, existing_df):
        assert language == "vie"
        assert year_from == 2000
        assert year_to == 2025
        return [
            {
                "title": "Sách Tiếng Việt 2010",
                "author": "Tác giả VN",
                "year": 2010,
                "language": "vie",
                "status": "new",
                "match_reason": "",
            }
        ]

    monkeypatch.setattr("backend.routers.crawler_router.crawl_and_prepare", fake_crawl)

    resp = client.post(
        "/api/v1/crawler/search",
        json={
            "query": "công nghệ",
            "language": "vie",
            "year_from": 2000,
            "year_to": 2025,
            "source": "all",
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["total_found"] == 1


def test_05_detect_duplicates_logic():
    """Kiểm tra logic phân loại duplicate / uncertain / new trong detect_duplicates."""
    existing_df = pd.DataFrame([
        {"book_id": "book_001", "title": "Đắc Nhân Tâm", "author": "Dale Carnegie", "isbn": "9781234567890"},
        {"book_id": "book_002", "title": "Nhà Giả Kim", "author": "Paulo Coelho", "isbn": "9780987654321"},
    ])

    candidates = [
        # Trùng chính xác ISBN
        {"title": "Bản In Khác", "author": "Ai Đó", "isbn": "9781234567890"},
        # Trùng tiêu đề và tác giả
        {"title": "Đắc Nhân Tâm", "author": "Dale Carnegie", "isbn": ""},
        # Nghi ngờ trùng tiêu đề (khác tác giả)
        {"title": "Nhà Giả Kim", "author": "Tác Giả Khác", "isbn": ""},
        # Sách mới hoàn toàn
        {"title": "Một Cuốn Sách Mới", "author": "Người Mới", "isbn": "9781111111111"},
    ]

    classified = detect_duplicates(candidates, existing_df)
    assert classified[0]["status"] == "duplicate"
    assert "ISBN trùng" in classified[0]["match_reason"]
    assert classified[1]["status"] == "duplicate"
    assert "Tên sách + tác giả trùng" in classified[1]["match_reason"]
    assert classified[2]["status"] == "uncertain"
    assert "Tên sách trùng (tác giả khác?)" in classified[2]["match_reason"]
    assert classified[3]["status"] == "new"


# ============================================================================
# PHẦN 2: RBAC & IMPORT PERMISSIONS TESTS
# ============================================================================

def test_06_crawler_permissions_rbac():
    """Kiểm tra RBAC: Guest bị 401, User thường bị 403, Admin được phép."""
    # Guest
    resp_unauth = client.get("/api/v1/crawler/unindexed")
    assert resp_unauth.status_code == 401

    # User
    resp_user = client.get("/api/v1/crawler/unindexed", headers=user_headers)
    assert resp_user.status_code == 403

    # Admin
    resp_admin = client.get("/api/v1/crawler/unindexed", headers=admin_headers)
    assert resp_admin.status_code == 200
    data = resp_admin.json()
    assert "total_books" in data
    assert "indexed_count" in data
    assert "count" in data
    assert "unindexed_books" in data


# ============================================================================
# PHẦN 3: CHROMADB VECTOR SYNC & UNINDEXED MANAGEMENT TESTS
# ============================================================================

def test_07_unindexed_books_detection(tmp_path):
    """Kiểm tra phát hiện chính xác sách trong CSV chưa có vector trong ChromaDB."""
    test_csv = tmp_path / "books.csv"
    books = [
        {"book_id": "book_001", "title": "Sách Đã Có Vector"},
        {"book_id": "book_002", "title": "Sách Chưa Có Vector 1"},
        {"book_id": "book_003", "title": "Sách Chưa Có Vector 2"},
    ]
    pd.DataFrame(books).to_csv(test_csv, index=False)

    # Giả lập ChromaDB SQLite chỉ có book_001
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir(parents=True)
    sqlite_path = chroma_dir / "chroma.sqlite3"
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE embeddings (embedding_id TEXT PRIMARY KEY)")
    cur.execute("INSERT INTO embeddings VALUES ('book_001')")
    conn.commit()
    conn.close()

    unindexed = get_unindexed_books(csv_path=test_csv, chroma_path=chroma_dir)
    assert len(unindexed) == 2
    unindexed_ids = {b["book_id"] for b in unindexed}
    assert unindexed_ids == {"book_002", "book_003"}


def test_08_sync_unindexed_books_upsert(tmp_path, monkeypatch):
    """Kiểm tra đồng bộ sách chưa index: gọi ingest và trả về kết quả chuẩn."""
    test_csv = tmp_path / "books.csv"
    books = [
        {"book_id": "book_001", "title": "Sách 1"},
        {"book_id": "book_002", "title": "Sách 2"},
    ]
    pd.DataFrame(books).to_csv(test_csv, index=False)

    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir(parents=True)
    sqlite_path = chroma_dir / "chroma.sqlite3"
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE embeddings (embedding_id TEXT PRIMARY KEY)")
    # Giả sử chưa có sách nào
    conn.commit()
    conn.close()

    def fake_ingest(books_to_ingest, gemini_api_key, chroma_path, max_retries=3, progress_callback=None):
        return {"upserted": len(books_to_ingest), "failed": 0}

    monkeypatch.setattr("crawler_service.ingest_books_to_chroma", fake_ingest)

    result = sync_unindexed_books_to_chroma(
        gemini_api_key="fake-key",
        csv_path=test_csv,
        chroma_path=chroma_dir,
    )
    assert result["upserted"] == 2
    assert result["failed"] == 0
    assert result["total_unindexed"] == 2


def test_09_sync_second_time_no_unindexed(tmp_path, monkeypatch):
    """Chạy sync lần hai khi toàn bộ sách đã có vector: trả về 0 sách cần sync."""
    test_csv = tmp_path / "books.csv"
    books = [{"book_id": "book_001", "title": "Sách 1"}]
    pd.DataFrame(books).to_csv(test_csv, index=False)

    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir(parents=True)
    sqlite_path = chroma_dir / "chroma.sqlite3"
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE embeddings (embedding_id TEXT PRIMARY KEY)")
    cur.execute("INSERT INTO embeddings VALUES ('book_001')")
    conn.commit()
    conn.close()

    result = sync_unindexed_books_to_chroma(
        gemini_api_key="fake-key",
        csv_path=test_csv,
        chroma_path=chroma_dir,
    )
    assert result["upserted"] == 0
    assert result["total_unindexed"] == 0


def test_10_sync_partial_failure_handling(tmp_path, monkeypatch):
    """Mô phỏng trường hợp 1 sách bị lỗi embedding: hệ thống ghi nhận failed mà không crash."""
    books = [
        {"book_id": "book_001", "title": "Sách Thành Công"},
        {"book_id": "book_002", "title": "Sách Thất Bại"},
    ]
    # Giả lập ingest trả về 1 upserted, 1 failed
    def fake_ingest(books_to_ingest, gemini_api_key, chroma_path, max_retries=3, progress_callback=None):
        return {"upserted": 1, "failed": 1}

    monkeypatch.setattr("crawler_service.ingest_books_to_chroma", fake_ingest)
    monkeypatch.setattr("crawler_service.get_unindexed_books", lambda *args, **kwargs: books)

    result = sync_unindexed_books_to_chroma(
        gemini_api_key="fake-key",
        csv_path=Path("dummy.csv"),
        chroma_path=Path("dummy_chroma"),
    )
    assert result["upserted"] == 1
    assert result["failed"] == 1
    assert result["total_unindexed"] == 2


def test_11_sync_endpoint_concurrent_lock(monkeypatch):
    """Tiến trình sync ChromaDB không cho phép chạy đồng thời gây xung đột dữ liệu (HTTP 409)."""
    from backend.routers import crawler_router

    # Khóa lock thủ công
    crawler_router._sync_lock.acquire(blocking=False)
    try:
        resp = client.post("/api/v1/crawler/sync-unindexed", headers=admin_headers)
        assert resp.status_code == 409
        assert "Tiến trình đồng bộ ChromaDB đang được thực hiện" in resp.json()["detail"]
    finally:
        crawler_router._sync_lock.release()


# ============================================================================
# PHẦN 4: REGRESSION TESTS (RAG, CHAT, BOOK ACTIONS, LOCATIONS)
# ============================================================================

def test_12_regression_rag_chat_anti_hallucination():
    """Xác nhận pipeline RAG chống bịa đặt vẫn hoạt động chuẩn xác với 208 sách hiện có."""
    profile = {"interests": ["Khoa học", "Tâm lý"], "favorite_genres": ["Kỹ năng sống"]}
    answer, source_nodes, intent = handle_user_message(
        question="Giới thiệu cho tôi cuốn sách Đắc Nhân Tâm",
        reader_profile=profile,
        top_k=3,
    )
    assert len(answer) > 10
    assert isinstance(source_nodes, list)


def test_13_regression_book_catalog_and_filter():
    """Xác nhận API kho sách (/api/v1/books) và bộ lọc vẫn hoạt động hoàn hảo."""
    resp = client.get("/api/v1/books?page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 10
    assert data["total"] == 208


def test_14_regression_location_search_bookstore_and_library():
    """Xác nhận API tìm kiếm địa điểm (/api/v1/locations/search) từ Giai đoạn 3 không bị ảnh hưởng."""
    resp = client.get("/api/v1/locations/search?query=Da%20Nang&kind=all")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "fallback_urls" in data
    assert "google_maps_bookstores" in data["fallback_urls"]
    assert "google_maps_libraries" in data["fallback_urls"]
