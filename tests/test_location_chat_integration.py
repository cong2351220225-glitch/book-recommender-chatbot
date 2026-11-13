import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from intent_router import (
    classify_intent,
    extract_user_location,
    FIND_BOOKSTORE,
    FIND_LIBRARY,
    LIBRARY_INFO,
)

client = TestClient(app)


def test_01_intent_recognition_bookstore_and_library():
    """1. Test nhận diện intent nhà sách và thư viện."""
    assert classify_intent("Tôi muốn tìm nhà sách gần đây.") == FIND_BOOKSTORE
    assert classify_intent("Tìm nhà sách ở Đà Nẵng.") == FIND_BOOKSTORE
    assert classify_intent("Cho tôi địa chỉ nhà sách gần đây.") == FIND_BOOKSTORE
    assert classify_intent("Tìm nơi bán cuốn sách này.") == FIND_BOOKSTORE
    assert classify_intent("Có thư viện nào gần quận Liên Chiểu không?") == FIND_LIBRARY
    assert classify_intent("Tìm thư viện gần Huế") == FIND_LIBRARY


def test_02_location_extraction():
    """2. Test trích xuất địa danh người dùng."""
    assert extract_user_location("Tìm nhà sách ở Đà Nẵng.") == "Đà Nẵng"
    assert extract_user_location("Có thư viện nào gần quận Liên Chiểu không?") == "quận Liên Chiểu"
    assert extract_user_location("tôi ở Đà Nẵng, tìm nhà sách gần tôi") == "Đà Nẵng"
    # Thiếu địa điểm cụ thể
    assert extract_user_location("Tôi muốn tìm nhà sách gần đây.") == ""
    assert extract_user_location("Cho tôi địa chỉ nhà sách gần đây.") == ""


def test_03_chat_message_with_location_success():
    """3. Test tìm nhà sách ở Đà Nẵng qua /api/v1/chat/message."""
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Tìm nhà sách ở Đà Nẵng.", "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == FIND_BOOKSTORE
    assert len(data.get("locations", [])) > 0
    # Dữ liệu thực từ SerpApi Google Maps
    first = data["locations"][0]
    assert "title" in first and first["title"]
    assert "address" in first and first["address"]
    assert "google_maps_url" in first and first["google_maps_url"].startswith("http")


def test_04_chat_message_missing_location_asks_user():
    """4. Test thiếu địa điểm thì hỏi người dùng thành phố/quận nào."""
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Tôi muốn tìm nhà sách gần đây."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == FIND_BOOKSTORE
    assert data.get("locations") == []
    answer = data.get("answer", "").lower()
    assert "khu vực" in answer or "thành phố" in answer or "quận" in answer


def test_05_chat_stream_with_location():
    """5. Test /api/v1/chat/stream trả về kết quả địa điểm nhất quán."""
    res = client.post(
        "/api/v1/chat/stream",
        json={"message": "Tìm nhà sách ở Đà Nẵng.", "top_k": 2},
    )
    assert res.status_code == 200
    lines = [line.strip() for line in res.text.split("\n") if line.startswith("data: ")]
    assert len(lines) > 0
    # Final done payload
    last_payload = json.loads(lines[-1][6:])
    assert last_payload.get("done") is True
    assert last_payload.get("intent") == FIND_BOOKSTORE
    assert len(last_payload.get("locations", [])) > 0


def test_06_regular_book_query_goes_through_rag():
    """6. Test câu hỏi sách thông thường vẫn đi qua RAG và thư viện số."""
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Thư viện hiện có bao nhiêu cuốn sách?", "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert "208" in data.get("answer", "")
    assert data.get("locations") == []
    assert data.get("intent") == LIBRARY_INFO


def test_07_rest_api_locations_search_direct():
    """7. Test endpoint REST API /api/v1/locations/search hoạt động trực tiếp."""
    res = client.get("/api/v1/locations/search?location=Da+Nang&kind=bookstore&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert data["location"] == "Da Nang"
    assert data["kind"] == "bookstore"
    assert len(data.get("results", [])) > 0
    assert "google_maps_bookstores" in data.get("fallback_urls", {})

