from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import get_books_df, get_authors_df
from book_service import search_books, get_book_by_id
from author_service import search_authors

client = TestClient(app)


def test_tc01_search_real_book():
    """TC-01: Tìm một sách có thật trong dữ liệu (tiếng Việt có dấu và không dấu)."""
    # Tìm kiếm qua API
    res = client.get("/api/v1/books?q=Clean%20Code")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    titles = [b["title"] for b in data["items"]]
    assert any("Clean Code" in t for t in titles)

    # Tìm kiếm không dấu
    res_no_accent = client.get("/api/v1/books?q=lap%20trinh")
    assert res_no_accent.status_code == 200
    assert res_no_accent.json()["total"] >= 1


def test_tc02_search_real_author():
    """TC-02: Tìm một tác giả có thật trong dữ liệu."""
    res = client.get("/api/v1/authors?q=Martin")
    assert res.status_code == 200
    authors = res.json()
    assert len(authors) >= 1
    names = [a["name"] for a in authors]
    assert any("Martin" in n for n in names)

    # Tìm kiếm tác giả Murakami
    res_author2 = client.get("/api/v1/authors?q=Murakami")
    assert res_author2.status_code == 200
    assert len(res_author2.json()) >= 1
    assert any("Murakami" in a["name"] for a in res_author2.json())


def test_tc03_filter_year_range():
    """TC-03: Lọc theo khoảng năm (min_year đến max_year)."""
    min_y = 2015
    max_y = 2022
    res = client.get(f"/api/v1/books?min_year={min_y}&max_year={max_y}")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    for book in items:
        assert min_y <= book["year"] <= max_y, f"Book {book['title']} year {book['year']} out of range"


def test_tc04_filter_min_rating():
    """TC-04: Lọc theo rating tối thiểu."""
    min_r = 4.5
    res = client.get(f"/api/v1/books?min_rating={min_r}")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    for book in items:
        assert book["rating"] >= min_r, f"Book {book['title']} rating {book['rating']} < {min_r}"


def test_tc05_filter_language_and_endpoint():
    """TC-05: Lấy danh sách ngôn ngữ thực tế và lọc theo ngôn ngữ."""
    res_lang = client.get("/api/v1/books/languages")
    assert res_lang.status_code == 200
    langs = res_lang.json()
    assert "Tiếng Việt" in langs
    assert "Tiếng Anh" in langs

    # Lọc sách theo Tiếng Việt
    res_vi = client.get("/api/v1/books?language=Tiếng%20Việt")
    assert res_vi.status_code == 200
    items_vi = res_vi.json()["items"]
    assert len(items_vi) > 0
    for book in items_vi:
        assert book["language"] == "Tiếng Việt"


def test_tc06_combine_at_least_three_filters():
    """TC-06: Kết hợp ít nhất ba điều kiện lọc (ngôn ngữ, khoảng năm, min_rating)."""
    res = client.get("/api/v1/books?language=Tiếng%20Việt&min_year=2000&max_year=2024&min_rating=4.0")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    for b in items:
        assert b["language"] == "Tiếng Việt"
        assert 2000 <= b["year"] <= 2024
        assert b["rating"] >= 4.0


def test_tc07_all_seven_sort_types():
    """TC-07: Kiểm tra tất cả 7 kiểu sắp xếp."""
    sort_orders = [
        "Phù hợp",
        "Tên A-Z",
        "Tên Z-A",
        "Năm mới nhất",
        "Năm cũ nhất",
        "Đánh giá cao",
        "Đánh giá thấp",
    ]
    for sort_name in sort_orders:
        res = client.get(f"/api/v1/books?sort_by={sort_name}&page_size=20")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) > 0

    # Kiểm tra tính đúng đắn của Tên A-Z vs Tên Z-A
    res_az = client.get("/api/v1/books?sort_by=Tên%20A-Z&page_size=10").json()["items"]
    res_za = client.get("/api/v1/books?sort_by=Tên%20Z-A&page_size=10").json()["items"]
    assert res_az[0]["title"] != res_za[0]["title"]

    # Kiểm tra Năm mới nhất vs Năm cũ nhất
    res_newest = client.get("/api/v1/books?sort_by=Năm%20mới%20nhất&page_size=10").json()["items"]
    res_oldest = client.get("/api/v1/books?sort_by=Năm%20cũ%20nhất&page_size=10").json()["items"]
    assert res_newest[0]["year"] >= res_newest[-1]["year"]
    assert res_oldest[0]["year"] <= res_oldest[-1]["year"]
    assert res_newest[0]["year"] > res_oldest[0]["year"]

    # Kiểm tra Đánh giá cao vs Đánh giá thấp
    res_high_r = client.get("/api/v1/books?sort_by=Đánh%20giá%20cao&page_size=10").json()["items"]
    res_low_r = client.get("/api/v1/books?sort_by=Đánh%20giá%20thấp&page_size=10").json()["items"]
    assert res_high_r[0]["rating"] >= res_high_r[-1]["rating"]
    assert res_low_r[0]["rating"] <= res_low_r[-1]["rating"]


def test_tc08_reset_filters_returns_full_catalog():
    """TC-08: Kiểm tra xóa bộ lọc trả về đầy đủ 208 cuốn sách."""
    res = client.get("/api/v1/books")
    assert res.status_code == 200
    assert res.json()["total"] == 208


def test_tc09_empty_and_error_handling():
    """TC-09: Kiểm tra query không tồn tại và xử lý an toàn."""
    res = client.get("/api/v1/books?q=xyznonexistentquery999999")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

    # Book detail not found returns 404 cleanly
    res_404 = client.get("/api/v1/books/nonexistent_id_999")
    assert res_404.status_code == 404
