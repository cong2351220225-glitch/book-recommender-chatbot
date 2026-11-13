from __future__ import annotations

from pathlib import Path

import reading_service
import pytest
import requests
import location_service
import rag_engine
from author_service import get_author_books, get_author_genres, load_authors, search_authors
from book_service import (
    filter_books,
    get_book_by_id,
    get_featured_books,
    get_related_books,
    load_books,
    search_books,
)
from intent_router import (
    BOOK_RECOMMENDATION_NEEDS_CONTEXT,
    FIND_BOOKSTORE,
    FIND_LIBRARY,
    GENERAL,
    LOCATION_BOOKSTORE,
    LOCATION_LIBRARY,
    SET_LOCATION,
    SMALL_TALK,
    classify_intent,
    extract_user_location,
    normalize_user_location,
)
from location_service import build_google_maps_search_url, build_maps_directions_url
from rag_engine import create_reader_profile, update_reader_profile
from reading_service import validate_local_file


def test_catalog_and_foreign_keys() -> None:
    books = load_books()
    authors = load_authors()
    assert len(books) >= 20
    non_empty_author_ids = {aid for aid in books["author_id"] if str(aid).strip()}
    assert non_empty_author_ids.issubset(set(authors["author_id"]))
    assert books["book_id"].is_unique


def test_book_and_author_search() -> None:
    books = load_books()
    authors = load_authors()
    assert not search_books(books, "AI").empty
    assert not search_authors(authors, "James Clear").empty


def test_catalog_filters_details_related_and_featured() -> None:
    books = load_books()
    atomic_habits = get_book_by_id("book_001", books)
    assert atomic_habits is not None
    assert len(filter_books(books, genre="Tâm lý")) == 3
    assert not search_books(books, "thói quen").empty
    assert not get_related_books(books, atomic_habits).empty
    assert not get_featured_books(books).empty


def test_author_works_and_genres() -> None:
    books = load_books()
    authors = load_authors()
    works = get_author_books(books, "james-clear", authors)
    assert len(works) == 1
    assert get_author_genres(books, "james-clear", authors) == ["Kỹ năng sống"]


def test_location_intents_and_urls() -> None:
    assert classify_intent("Tìm nhà sách gần tôi") == LOCATION_BOOKSTORE
    assert classify_intent("Tìm thư viện gần Huế") == LOCATION_LIBRARY
    assert "google.com/maps/search" in build_google_maps_search_url("library", "Đà Nẵng")
    assert "google.com/maps/dir" in build_maps_directions_url("Huế", "Thư viện trung tâm")


def test_chat_location_intents_and_extraction() -> None:
    assert classify_intent("tôi ở Đà Nẵng") == SET_LOCATION
    assert classify_intent("Đà Nẵng") == SET_LOCATION
    assert classify_intent("tìm nhà sách ở Đà Nẵng") == FIND_BOOKSTORE
    assert classify_intent("tìm thư viện ở Huế") == FIND_LIBRARY
    assert classify_intent("nhà sách gần tôi") == FIND_BOOKSTORE
    assert classify_intent("thư viện gần tôi") == FIND_LIBRARY
    assert classify_intent("tôi ở Đà Nẵng, tìm nhà sách gần tôi") == FIND_BOOKSTORE
    assert classify_intent("tôi ở Đà Nẵng, tìm nơi mua sách Deep Learning") == FIND_BOOKSTORE
    assert extract_user_location("tôi ở Đà Nẵng, tìm nhà sách gần tôi") == "Đà Nẵng"
    assert normalize_user_location("đà nẵng") == "Đà Nẵng"


def test_general_assistant_routing_does_not_start_recommendation() -> None:
    assert classify_intent("Python là gì?") == GENERAL
    assert classify_intent("Giải thích machine learning đơn giản") == GENERAL
    assert classify_intent("Viết giúp tôi một email xin nghỉ học") == GENERAL
    assert classify_intent("SQL JOIN là gì?") == GENERAL
    assert classify_intent("Tôi buồn") == SMALL_TALK
    assert classify_intent("Tìm sách về AI") in {"book_search", "book_query"}
    assert classify_intent("Tìm sách Python cho người mới") in {"book_search", "book_query"}


def test_general_message_skips_rag_and_recommendation_starts_explicitly(monkeypatch) -> None:
    monkeypatch.setattr(rag_engine, "generate_general_response", lambda question, history: "GENERAL_REPLY")
    profile = create_reader_profile()
    answer, books, intent = rag_engine.handle_user_message("Python là gì?", reader_profile=profile)
    assert answer == "GENERAL_REPLY"
    assert books == []
    assert intent == rag_engine.OUT_OF_DOMAIN

    interview_answer, interview_books, interview_intent = rag_engine.handle_user_message(
        "Tôi muốn tìm một cuốn sách phù hợp với tôi.", reader_profile=create_reader_profile()
    )
    assert "chủ đề" in interview_answer.lower()
    assert interview_books == []
    assert interview_intent == rag_engine.BOOK_RECOMMENDATION_NEEDS_CONTEXT


def test_serpapi_location_normalization_and_query(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "local_results": [{
                    "title": "Nhà sách Demo",
                    "address": "1 Đường Mẫu, Huế",
                    "rating": 4.5,
                    "reviews": 120,
                    "type": "Book store",
                    "open_state": "Đang mở",
                    "phone": "0123",
                    "website": "https://example.com",
                    "gps_coordinates": {"latitude": 16.4637, "longitude": 107.5909},
                    "place_id": "place-1",
                    "data_id": "data-1",
                    "links": {"directions": "https://maps.example/directions"},
                }]
            }

    captured: dict = {}

    def fake_get(url, params, timeout):
        captured.update({"url": url, "params": params, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setattr(location_service.requests, "get", fake_get)
    results = location_service.search_bookstores("Huế", limit=3)
    assert results[0]["title"] == "Nhà sách Demo"
    assert results[0]["latitude"] == 16.4637
    assert results[0]["longitude"] == 107.5909
    assert results[0]["directions_url"] == "https://maps.example/directions"
    assert captured["params"]["q"] == "nhà sách tại Huế"
    assert captured["params"]["engine"] == "google_maps"


def test_serpapi_place_specific_fallback_url(monkeypatch) -> None:
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"local_results": [{"title": "Thư viện Mẫu", "address": "12 Đường Sách, Huế"}]}

    monkeypatch.setattr(location_service, "_api_key", lambda: "test-key")
    monkeypatch.setattr(location_service.requests, "get", lambda *args, **kwargs: Response())
    result = location_service.search_libraries("Huế", 1)[0]
    assert "Th%C6%B0+vi%E1%BB%87n+M%E1%BA%ABu" in result["google_maps_url"]
    assert "google.com/maps/dir" in result["directions_url"]


def test_serpapi_place_results_fallback_schema(monkeypatch) -> None:
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"place_results": {"title": "Thư viện Đà Nẵng", "address": "Đà Nẵng", "rating": 4.5}}

    monkeypatch.setattr(location_service, "_api_key", lambda: "test-key")
    monkeypatch.setattr(location_service.requests, "get", lambda *args, **kwargs: Response())
    results = location_service.search_libraries("Đà Nẵng", 3)
    assert len(results) == 1
    assert results[0]["title"] == "Thư viện Đà Nẵng"


def test_serpapi_missing_key_http_error_and_empty_results(monkeypatch) -> None:
    monkeypatch.setattr(location_service, "_api_key", lambda: "")
    with pytest.raises(location_service.LocationServiceError, match="Thiếu SERPAPI_API_KEY"):
        location_service.search_libraries("Huế")

    class ErrorResponse:
        def raise_for_status(self):
            raise requests.HTTPError("401")

    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setattr(location_service, "_api_key", lambda: "test-key")
    monkeypatch.setattr(location_service.requests, "get", lambda *args, **kwargs: ErrorResponse())
    with pytest.raises(location_service.LocationServiceError, match="HTTP không xác định"):
        location_service.search_libraries("Huế")

    class EmptyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"local_results": []}

    monkeypatch.setattr(location_service.requests, "get", lambda *args, **kwargs: EmptyResponse())
    with pytest.raises(location_service.LocationServiceError, match="Không tìm thấy"):
        location_service.search_libraries("Huế")


def test_intents_and_maps() -> None:
    assert classify_intent("Xin chào") == SMALL_TALK
    assert classify_intent("Tôi muốn tìm sách phù hợp với tôi") == BOOK_RECOMMENDATION_NEEDS_CONTEXT
    assert "google.com/maps/search" in build_google_maps_search_url("library", "Đà Nẵng")


def test_reading_path_security() -> None:
    assert validate_local_file("../../.env") is None
    assert validate_local_file(str(Path("C:/secret.pdf"))) is None


def test_reading_extensions_and_profile_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(reading_service, "READING_DIR", tmp_path)
    (tmp_path / "demo.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "demo.epub").write_bytes(b"PK")
    (tmp_path / "demo.txt").write_text("not a book")
    assert validate_local_file("demo.pdf") == tmp_path / "demo.pdf"
    assert validate_local_file("demo.epub") == tmp_path / "demo.epub"
    assert validate_local_file("demo.txt") is None
    assert validate_local_file("../demo.pdf") is None

    profile = create_reader_profile()
    update_reader_profile(profile, "Tôi muốn phát triển bản thân và gần đây mất động lực")
    update_reader_profile(profile, "Tôi thích sách dễ đọc về kỹ năng sống")
    assert profile["goal"] == "phát triển bản thân"
    assert profile["mood"] == "muốn lấy lại động lực"
    assert "kỹ năng sống" in profile["genres"]
    assert profile["difficulty"] == "dễ đọc"
