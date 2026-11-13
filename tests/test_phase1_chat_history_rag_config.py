from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import CHAT_HISTORY_DIR
from backend.core.security import create_access_token

client = TestClient(app)


def test_rag_config_endpoint():
    """Verify GET /api/v1/chat/config returns actual ChromaDB count and Top-K bounds."""
    res = client.get("/api/v1/chat/config")
    assert res.status_code == 200
    data = res.json()
    assert "vector_count" in data
    assert data["vector_count"] >= 208
    assert data["default_top_k"] == 3
    assert data["max_top_k"] == 10
    assert data["min_top_k"] == 1
    assert data["collection_name"] == "books_collection"


def test_chat_sessions_lifecycle_and_user_isolation():
    """Verify chat session creation, listing, switching, and user isolation."""
    user1 = "test_user_phase1_a"
    user2 = "test_user_phase1_b"

    token1 = create_access_token({"sub": user1})
    token2 = create_access_token({"sub": user2})

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    session_a = "sess_p1_alpha"
    session_b = "sess_p1_beta"

    # Send message in session A for user 1
    res1 = client.post(
        "/api/v1/chat/message",
        headers=headers1,
        json={"message": "Xin chào thủ thư phiên A", "session_id": session_a, "top_k": 3},
    )
    assert res1.status_code == 200

    # Send message in session B for user 1
    res2 = client.post(
        "/api/v1/chat/message",
        headers=headers1,
        json={"message": "Xin chào thủ thư phiên B", "session_id": session_b, "top_k": 5},
    )
    assert res2.status_code == 200

    # User 1 lists sessions: must see both sessions
    list1 = client.get("/api/v1/chat/sessions", headers=headers1)
    assert list1.status_code == 200
    sessions1 = list1.json()["sessions"]
    session_ids1 = [s["id"] for s in sessions1]
    assert session_a in session_ids1
    assert session_b in session_ids1

    # User 2 lists sessions: MUST NOT see User 1's sessions
    list2 = client.get("/api/v1/chat/sessions", headers=headers2)
    assert list2.status_code == 200
    sessions2 = list2.json()["sessions"]
    session_ids2 = [s["id"] for s in sessions2]
    assert session_a not in session_ids2
    assert session_b not in session_ids2

    # User 2 attempts to get User 1's session history: 403 Forbidden
    res_forbidden = client.get(f"/api/v1/chat/history/{session_a}", headers=headers2)
    assert res_forbidden.status_code == 403

    # User 2 attempts to delete User 1's session: 403 Forbidden
    res_del_forbidden = client.delete(f"/api/v1/chat/sessions/{session_a}", headers=headers2)
    assert res_del_forbidden.status_code == 403

    # User 1 deletes session A
    res_del = client.delete(f"/api/v1/chat/sessions/{session_a}", headers=headers1)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # After deletion, session A is gone, session B remains
    list1_after = client.get("/api/v1/chat/sessions", headers=headers1)
    session_ids_after = [s["id"] for s in list1_after.json()["sessions"]]
    assert session_a not in session_ids_after
    assert session_b in session_ids_after

    # Clean up session B
    client.delete(f"/api/v1/chat/sessions/{session_b}", headers=headers1)


def test_top_k_parameter_validation():
    """Verify Top-K values (1, 5, 10) are accepted and boundaries enforced."""
    # Valid bounds
    for k in [1, 5, 10]:
        res = client.post(
            "/api/v1/chat/message",
            json={"message": "alo", "top_k": k, "session_id": f"test_k_{k}"},
        )
        assert res.status_code == 200

    # Invalid bounds (<1 or >10)
    res_low = client.post(
        "/api/v1/chat/message",
        json={"message": "alo", "top_k": 0},
    )
    assert res_low.status_code == 422

    res_high = client.post(
        "/api/v1/chat/message",
        json={"message": "alo", "top_k": 11},
    )
    assert res_high.status_code == 422

