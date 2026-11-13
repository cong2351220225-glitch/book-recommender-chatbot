"""
Acceptance Test Suite for Phase 3:
Locations Feature & Quick Action Buttons on Book Detail.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from book_service import purchase_search_url
from location_service import (
    build_google_maps_search_url,
    build_maps_directions_url,
    normalize_local_result,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_build_google_maps_search_url_bookstore():
    url = build_google_maps_search_url("nhà sách", "Đà Nẵng")
    assert "google.com/maps/search/" in url
    assert "nh%C3%A0+s%C3%A1ch" in url
    assert "%C4%90%C3%A0+N%E1%BA%B5ng" in url


def test_build_google_maps_search_url_library():
    url = build_google_maps_search_url("thư viện", "Đà Nẵng")
    assert "google.com/maps/search/" in url
    assert "th%C6%B0+vi%E1%BB%87n" in url
    assert "%C4%90%C3%A0+N%E1%BA%B5ng" in url


def test_build_google_maps_search_url_english_aliases():
    url_bs = build_google_maps_search_url("bookstore", "Huế")
    assert "nh%C3%A0+s%C3%A1ch" in url_bs

    url_lib = build_google_maps_search_url("library", "Hà Nội")
    assert "th%C6%B0+vi%E1%BB%87n" in url_lib


def test_build_maps_directions_url():
    url = build_maps_directions_url("Vị trí của tôi", "Nhà sách Phương Nam Đà Nẵng")
    assert "google.com/maps/dir/" in url
    assert "V%E1%BB%8B+tr%C3%AD+c%E1%BB%A7a+t%C3%B4i" in url
    assert "Ph%C6%B0%C6%A1ng+Nam" in url


def test_purchase_search_url():
    url = purchase_search_url("Đắc Nhân Tâm")
    assert "google.com/search?q=" in url
    assert "%C4%90%E1%BA%AFc+Nh%C3%A2n+T%C3%A2m+mua+s%C3%A1ch" in url


def test_normalize_local_result_contract():
    raw_item = {
        "title": "Nhà Sách Test",
        "address": "123 Đường Sách, Q.1, TP.HCM",
        "rating": 4.6,
        "reviews": 120,
        "phone": "028 1234 5678",
        "open_state": "Mở cửa cả ngày",
        "website": "https://example.com/books",
        "gps_coordinates": {"latitude": 10.7769, "longitude": 106.7009},
    }
    normalized = normalize_local_result(raw_item, "bookstore", "TP.HCM")
    assert normalized["title"] == "Nhà Sách Test"
    assert normalized["address"] == "123 Đường Sách, Q.1, TP.HCM"
    assert normalized["rating"] == 4.6
    assert normalized["reviews"] == 120
    assert normalized["phone"] == "028 1234 5678"
    assert normalized["open_state"] == "Mở cửa cả ngày"
    assert normalized["website"] == "https://example.com/books"
    assert normalized["latitude"] == 10.7769
    assert normalized["longitude"] == 106.7009
    assert "google_maps_url" in normalized
    assert "directions_url" in normalized


def test_api_location_search_contract(client: TestClient):
    response = client.get("/api/v1/locations/search?location=Đà Nẵng&kind=bookstore&limit=3")
    assert response.status_code == 200
    data = response.json()

    assert data["location"] == "Đà Nẵng"
    assert data["kind"] == "bookstore"
    assert "results" in data
    assert isinstance(data["results"], list)
    assert "fallback_urls" in data
    assert "google_maps_bookstores" in data["fallback_urls"]
    assert "google_maps_libraries" in data["fallback_urls"]
    assert "th%C6%B0+vi%E1%BB%87n" in data["fallback_urls"]["google_maps_libraries"]

    if data["results"]:
        first = data["results"][0]
        assert "title" in first
        assert "address" in first
        assert "rating" in first
        assert "google_maps_url" in first


def test_api_location_search_libraries(client: TestClient):
    response = client.get("/api/v1/locations/search?location=Huế&kind=library&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "library"
    assert "fallback_urls" in data


def test_api_location_search_all_kind(client: TestClient):
    response = client.get("/api/v1/locations/search?location=Đà Nẵng&kind=all&limit=4")
    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "all"
    assert len(data["results"]) <= 4

