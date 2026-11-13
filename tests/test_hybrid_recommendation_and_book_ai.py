from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.services.recommendation_service import (
    build_user_interaction_matrix,
    compute_collaborative_filtering_scores,
    recommend_for_user,
)
from backend.core.security import create_access_token

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Collaborative Filtering Unit & Matrix Tests
# ---------------------------------------------------------------------------

def test_cf_interaction_matrix_build():
    matrix = build_user_interaction_matrix()
    assert isinstance(matrix, dict)
    assert len(matrix) > 0, "Expected existing users in interaction matrix"
    # Verify non-empty weights
    for u, bks in list(matrix.items())[:5]:
        assert isinstance(bks, dict)
        for b_id, w in bks.items():
            assert isinstance(w, (int, float))
            assert w > 0


def test_cf_cold_start_handling():
    # Cold start: Non-existent or new user with zero history
    matrix = build_user_interaction_matrix()
    scores = compute_collaborative_filtering_scores(
        username="brand_new_cold_user_99999",
        user_matrix=matrix,
        excluded_bids=set(),
    )
    assert scores == {}, "Cold start user must return empty CF scores without error"


def test_cf_multi_user_overlap_and_scoring():
    # Synthetic test scenario with 3 users to test CF formula deterministically
    mock_matrix = {
        "user_a": {"book_001": 3.0, "book_002": 3.0},
        "user_b": {"book_001": 3.0, "book_002": 3.0, "book_003": 3.0},
        "user_c": {"book_999": 3.0},
    }
    # User A is identical to User B on 001 and 002. User B has 003. User A does not have 003.
    scores = compute_collaborative_filtering_scores(
        username="user_a",
        user_matrix=mock_matrix,
        excluded_bids=set(),
    )
    assert "book_003" in scores
    assert scores["book_003"] > 0
    # user_c has no overlap, so book_999 should have 0 or not be in scores
    assert "book_999" not in scores


# ---------------------------------------------------------------------------
# 2. Hybrid & Collaborative Recommendation API Tests
# ---------------------------------------------------------------------------

def test_hybrid_recommendation_endpoint_guest():
    res = client.get("/api/v1/recommendations/for-you?algorithm=hybrid&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "hybrid"
    assert len(data["recommendations"]) <= 5
    assert len(data["recommendations"]) > 0


def test_collaborative_recommendation_endpoint_authenticated():
    token = create_access_token(data={"sub": "contract_reader", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/v1/recommendations/for-you?algorithm=collaborative&limit=5",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "collaborative"
    assert len(data["recommendations"]) > 0


def test_content_based_recommendation_endpoint():
    token = create_access_token(data={"sub": "contract_tester", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/v1/recommendations/for-you?algorithm=content_based&limit=5",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "content_based"
    assert len(data["recommendations"]) > 0


# ---------------------------------------------------------------------------
# 3. AI Book Summarization Tests (Full Text vs Metadata)
# ---------------------------------------------------------------------------

def test_ai_summarization_with_full_text():
    # book_203 has valid full text at data/sample_books/book_203.pdf
    res = client.post(
        "/api/v1/books/book_203/summary",
        json={"summary_type": "short"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == "book_203"
    assert data["source_type"] == "full_text"
    assert data["has_full_text"] is True
    assert len(data["summary"]) > 0
    assert "Bản tóm tắt được trích xuất" in data["notice"]


def test_ai_summarization_with_metadata_only():
    # book_001 (Atomic Habits) has no local full-text pdf, must gracefully summarize metadata
    res = client.post(
        "/api/v1/books/book_001/summary",
        json={"summary_type": "short"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == "book_001"
    assert data["source_type"] == "metadata"
    assert data["has_full_text"] is False
    assert len(data["summary"]) > 0
    assert "chưa có bản đọc toàn văn" in data["notice"]


def test_ai_summarization_404_not_found():
    res = client.post(
        "/api/v1/books/non_existent_book_99999/summary",
        json={"summary_type": "short"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 4. Isolated Book-specific Q&A Tests
# ---------------------------------------------------------------------------

def test_book_qa_valid_isolated_answer():
    res = client.post(
        "/api/v1/books/book_203/qa",
        json={"question": "Cuốn sách này nói về điều gì và có tài liệu gì trong thư viện?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == "book_203"
    assert len(data["answer"]) > 0
    assert data["context_source"] == "full_text"


def test_book_qa_disclaims_out_of_context():
    # Ask about an irrelevant subject or book outside book_001's scope
    res = client.post(
        "/api/v1/books/book_001/qa",
        json={"question": "Cuốn sách này có bao nhiêu trang viết về cách nấu món bún bò Huế?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == "book_001"
    # Should politely clarify information is not in the book
    assert "không có trong tài liệu" in data["answer"].lower() or data["has_sufficient_context"] is False


def test_book_qa_404_not_found():
    res = client.post(
        "/api/v1/books/non_existent_book_99999/qa",
        json={"question": "Cuốn sách này nói về gì?"},
    )
    assert res.status_code == 404

