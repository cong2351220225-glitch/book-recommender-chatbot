import copy
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import pandas as pd

from backend.main import app
from backend.core.security import create_access_token
from crawler_service import BOOK_FIELDS, save_books_to_csv

client = TestClient(app)

ADMIN_USER = {"username": "admin", "role": "admin", "full_name": "Library Administrator"}
NORMAL_USER = {"username": "reader_user", "role": "user", "full_name": "Test Reader"}

admin_token = create_access_token(data={"sub": ADMIN_USER["username"], "role": ADMIN_USER["role"]})
admin_headers = {"Authorization": f"Bearer {admin_token}"}

user_token = create_access_token(data={"sub": NORMAL_USER["username"], "role": NORMAL_USER["role"]})
user_headers = {"Authorization": f"Bearer {user_token}"}


def test_01_crawler_sources_endpoint():
    """Endpoint GET /api/v1/crawler/sources trả về đầy đủ 6 nguồn dữ liệu số chuẩn."""
    response = client.get("/api/v1/crawler/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    sources = data["sources"]
    source_ids = {s["id"] for s in sources}

    expected_sources = {
        "all",
        "openlibrary",
        "google_books",
        "gutenberg",
        "internet_archive",
        "europeana",
        "itunes",
    }
    assert expected_sources.issubset(source_ids)
    assert len(sources) >= 7


def test_02_guest_forbidden():
    """Khách chưa đăng nhập (Guest) bị từ chối truy cập 401 với các thao tác Admin crawler."""
    dummy_payload = {
        "candidate": {"title": "Test Book", "author": "Author"},
        "upsert_chroma": False,
    }
    resp_single = client.post("/api/v1/crawler/import", json=dummy_payload)
    assert resp_single.status_code == 401

    resp_batch = client.post(
        "/api/v1/crawler/batch-import",
        json={"candidates": [{"title": "Book 1"}], "upsert_chroma": False},
    )
    assert resp_batch.status_code == 401

    resp_unindexed = client.get("/api/v1/crawler/unindexed")
    assert resp_unindexed.status_code == 401


def test_03_normal_user_forbidden():
    """Người dùng thông thường (role: user) bị từ chối 403 Forbidden với crawler management."""
    dummy_payload = {
        "candidate": {"title": "Unauthorized Import Book", "author": "Unknown"},
        "upsert_chroma": False,
    }
    resp_single = client.post(
        "/api/v1/crawler/import",
        json=dummy_payload,
        headers=user_headers,
    )
    assert resp_single.status_code == 403

    resp_batch = client.post(
        "/api/v1/crawler/batch-import",
        json={"candidates": [{"title": "Book 1"}], "upsert_chroma": False},
        headers=user_headers,
    )
    assert resp_batch.status_code == 403

    resp_unindexed = client.get("/api/v1/crawler/unindexed", headers=user_headers)
    assert resp_unindexed.status_code == 403


def test_04_search_crawler_sources_contract():
    """API tìm kiếm nguồn crawler trả về đúng cấu trúc CrawlSearchResponse."""
    # Test với mock hoặc tìm kiếm nhẹ nhàng
    search_payload = {
        "query": "artificial intelligence",
        "source": "openlibrary",
        "limit": 3,
    }
    response = client.post("/api/v1/crawler/search", json=search_payload)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "source" in data
    assert "total_found" in data
    assert "results" in data
    assert isinstance(data["results"], list)


def test_05_prevent_duplicate_import(tmp_path, monkeypatch):
    """Cơ chế chống trùng lặp từ chối nhập sách khi đã có trong thư viện."""
    # Tạo isolated csv file dựa trên data/books.csv để không làm hỏng dữ liệu gốc
    real_csv = Path("data/books.csv")
    test_csv = tmp_path / "books_test.csv"
    if real_csv.exists():
        df_real = pd.read_csv(real_csv)
        df_real.to_csv(test_csv, index=False, encoding="utf-8-sig")
        existing_title = df_real.iloc[0]["title"]
        existing_isbn = str(df_real.iloc[0].get("isbn", ""))
    else:
        existing_title = "Tiêu đề đã có"
        existing_isbn = "9781234567890"
        df_dummy = pd.DataFrame([{"book_id": "book_001", "title": existing_title, "isbn": existing_isbn}])
        df_dummy.to_csv(test_csv, index=False, encoding="utf-8-sig")

    monkeypatch.setattr("backend.routers.crawler_router.BOOKS_CSV_PATH", test_csv)

    # Thử import lại đúng cuốn sách đã tồn tại
    duplicate_candidate = {
        "title": existing_title,
        "author": "Any Author",
        "isbn": existing_isbn,
        "description": "Thử nghiệm trùng lặp",
    }
    resp = client.post(
        "/api/v1/crawler/import",
        json={"candidate": duplicate_candidate, "upsert_chroma": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is False
    assert "đã tồn tại" in res_data["message"]
    assert res_data["book_id"] is None


def test_06_batch_import_deduplication_and_isolation(tmp_path, monkeypatch):
    """Batch import xử lý kết hợp sách trùng và sách mới, trả về kết quả từng cuốn."""
    test_csv = tmp_path / "books_batch_test.csv"
    initial_books = [
        {"book_id": "book_001", "title": "Sách Hiện Có 1", "author": "Tác giả 1", "isbn": "978000000001"},
        {"book_id": "book_002", "title": "Sách Hiện Có 2", "author": "Tác giả 2", "isbn": "978000000002"},
    ]
    pd.DataFrame(initial_books).to_csv(test_csv, index=False, encoding="utf-8-sig")
    monkeypatch.setattr("backend.routers.crawler_router.BOOKS_CSV_PATH", test_csv)

    batch_candidates = [
        {
            "title": "Sách Hiện Có 1", # Sách trùng
            "author": "Tác giả 1",
            "isbn": "978000000001",
        },
        {
            "title": "Sách Mới Hoàn Toàn 2026", # Sách mới
            "author": "AI Researcher",
            "isbn": "978999999999",
            "description": "Mô tả sách nghiên cứu mới",
            "year": 2026,
            "genre": "Công nghệ",
        },
    ]

    resp = client.post(
        "/api/v1/crawler/batch-import",
        json={"candidates": batch_candidates, "upsert_chroma": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requested"] == 2
    assert data["imported_count"] == 1
    assert data["skipped_count"] == 1
    assert len(data["results"]) == 2

    # Cuốn 1 bị từ chối
    item1 = data["results"][0]
    assert item1["title"] == "Sách Hiện Có 1"
    assert item1["success"] is False
    assert item1["book_id"] is None

    # Cuốn 2 được duyệt và cấp ID mới
    item2 = data["results"][1]
    assert item2["title"] == "Sách Mới Hoàn Toàn 2026"
    assert item2["success"] is True
    assert item2["book_id"] == "book_003"

    # Kiểm tra CSV đã được thêm đúng 1 cuốn mới
    updated_df = pd.read_csv(test_csv)
    assert len(updated_df) == 3
    assert updated_df.iloc[2]["title"] == "Sách Mới Hoàn Toàn 2026"


def test_07_metadata_schema_conformity():
    """Xác nhận schema chuẩn 26 trường của sách khi crawler nhập."""
    assert len(BOOK_FIELDS) == 26
    expected_fields = [
        "book_id", "title", "author", "author_id", "genre", "description",
        "year", "isbn", "publisher", "pages", "language", "format",
        "cover_url", "rating", "featured", "tags", "target_audience",
        "mood", "difficulty", "summary", "reading_available", "reading_type",
        "reading_url", "local_file", "purchase_url", "library_url"
    ]
    for field in expected_fields:
        assert field in BOOK_FIELDS
