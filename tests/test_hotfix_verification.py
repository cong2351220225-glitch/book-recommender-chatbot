from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.services.recommendation_service import (
    recommend_for_user,
    recommend_continue_reading,
    build_user_interaction_matrix,
)

client = TestClient(app)


# ===========================================================================
# 1. Tests for Bug 1: Bookshelf Exclusion & Collaborative Filtering Keys
# ===========================================================================

def test_bookshelf_exclusion_in_recommend_for_user():
    """
    Verify that books in a user's bookshelf (favorite, reading, completed)
    with actual JSON structure (UUID keys and separate 'book_id', 'status')
    are strictly excluded from candidate recommendations.
    """
    mock_shelf = {
        "username": "test_shelf_user",
        "items": {
            "book_001_favorite_eaa397": {
                "id": "book_001_favorite_eaa397",
                "book_id": "book_001",
                "status": "favorite",
                "added_at": "2026-11-01T10:00:00",
            },
            "book_002_reading_fbb123": {
                "id": "book_002_reading_fbb123",
                "book_id": "book_002",
                "status": "reading",
                "added_at": "2026-11-01T11:00:00",
            },
            "book_003_completed_999aaa": {
                "id": "book_003_completed_999aaa",
                "book_id": "book_003",
                "status": "completed",
                "added_at": "2026-11-01T12:00:00",
            },
        },
    }

    mock_user_data = {
        "username": "test_shelf_user",
        "preferences": {"preferred_genres": ["Kỹ năng sống", "Kinh doanh"], "preferred_authors": []},
        "feedback": {},
    }

    with patch("backend.services.recommendation_service._load_user_bookshelf", return_value=mock_shelf):
        with patch("backend.services.recommendation_service.load_user_recommendation_data", return_value=mock_user_data):
            # Test Hybrid algorithm
            results, basis, modified = recommend_for_user("test_shelf_user", limit=10, algorithm="hybrid")
            rec_bids = {item["book_id"] for item in results}
            assert "book_001" not in rec_bids, "book_001 (favorite) must be excluded from recommendations"
            assert "book_002" not in rec_bids, "book_002 (reading) must be excluded from recommendations"
            assert "book_003" not in rec_bids, "book_003 (completed) must be excluded from recommendations"

            # Test Collaborative algorithm
            results_cf, basis_cf, _ = recommend_for_user("test_shelf_user", limit=10, algorithm="collaborative")
            rec_bids_cf = {item["book_id"] for item in results_cf}
            assert "book_001" not in rec_bids_cf, "book_001 must be excluded from CF recommendations"
            assert "book_002" not in rec_bids_cf, "book_002 must be excluded from CF recommendations"
            assert "book_003" not in rec_bids_cf, "book_003 must be excluded from CF recommendations"


def test_recommend_continue_reading_uses_actual_book_id():
    """
    Verify recommend_continue_reading extracts book_id from shelf item dict
    rather than using the dictionary key UUID.
    """
    mock_shelf = {
        "username": "reader_user",
        "items": {
            "book_001_reading_uuid_abc": {
                "id": "book_001_reading_uuid_abc",
                "book_id": "book_001",
                "status": "reading",
                "progress_page": 25,
                "total_pages": 300,
            }
        },
    }

    with patch("backend.services.recommendation_service._load_user_bookshelf", return_value=mock_shelf):
        results = recommend_continue_reading("reader_user", limit=4)
        assert isinstance(results, list)
        assert len(results) > 0, "Should recommend similar books based on active reading book_001"
        for r in results:
            assert r["book_id"] != "book_001", "The active reading book itself should not be recommended"
            assert r["reason_type"] == "continue_reading"


def test_cold_start_new_user_unaffected():
    """
    Verify that a brand new user with empty shelf and no preferences
    smoothly receives cold-start recommendations.
    """
    mock_empty_shelf = {"username": "cold_user", "items": {}}
    mock_user_data = {"username": "cold_user", "preferences": {}, "feedback": {}}

    with patch("backend.services.recommendation_service._load_user_bookshelf", return_value=mock_empty_shelf):
        with patch("backend.services.recommendation_service.load_user_recommendation_data", return_value=mock_user_data):
            results, basis, modified = recommend_for_user("cold_user", limit=5)
            assert len(results) == 5
            assert "Gợi ý khởi đầu" in basis


# ===========================================================================
# 2. Tests for Bug 2: Book-specific Q&A Fallback and Isolation
# ===========================================================================

def test_book_qa_fallback_rejects_irrelevant_cross_book_question():
    """
    When Gemini API raises an exception (quota 429 or offline),
    an irrelevant question (e.g. asking about Broken Window Theory on book_001)
    MUST be rejected cleanly without returning mismatched book description lines.
    """
    with patch("backend.routers.book_router.get_gemini_client") as mock_client:
        mock_client.side_effect = Exception("ResourceExhausted: 429 Quota Exceeded")

        resp = client.post(
            "/api/v1/books/book_001/qa",
            json={
                "question": "Nguyên lý chiếc cửa sổ vỡ (Broken Window Theory) và tư duy lập trình thực dụng được nói đến ở đâu trong cuốn sách này?"
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["book_id"] == "book_001"
        assert data["has_sufficient_context"] is False
        assert "không có trong tài liệu của cuốn sách" in data["answer"].lower()


def test_book_qa_fallback_rejects_stopwords_only_question():
    """
    A question containing only stop words or vague questioning words
    must not match random lines in fallback mode.
    """
    with patch("backend.routers.book_router.get_gemini_client") as mock_client:
        mock_client.side_effect = Exception("429 Quota Exceeded")

        resp = client.post(
            "/api/v1/books/book_001/qa",
            json={"question": "Cuốn sách này nói gì ở đâu thế nào vậy bạn?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_sufficient_context"] is False
        assert "không có trong tài liệu của cuốn sách" in data["answer"].lower()


def test_book_qa_fallback_matches_relevant_keywords():
    """
    When the question genuinely matches multiple core keywords in the book's context,
    the fallback mode should return the relevant excerpt with has_sufficient_context=True.
    """
    with patch("backend.routers.book_router.get_gemini_client") as mock_client:
        mock_client.side_effect = Exception("429 Quota Exceeded")

        # book_001 is Atomic Habits by James Clear (thói quen, thay đổi nhỏ)
        resp = client.post(
            "/api/v1/books/book_001/qa",
            json={"question": "Phương pháp xây dựng thói quen tích cực của tác giả James Clear là gì?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_sufficient_context"] is True
        assert "Dựa trên thông tin của cuốn sách" in data["answer"]
