from __future__ import annotations

import os
import sys
import json
import uuid
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# -------------------------------------------------------------
# 1. Standard Chat Message Endpoint
# -------------------------------------------------------------
def test_01_chat_message_standard():
    test_session = f"test_session_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Xin chào thư viện!", "session_id": test_session, "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "intent" in data
    assert data["session_id"] == test_session
    assert "books" in data
    assert isinstance(data["books"], list)


# -------------------------------------------------------------
# 2. SSE Streaming Protocol & Event Chunks
# -------------------------------------------------------------
def test_02_chat_stream_protocol():
    test_session = f"test_stream_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/chat/stream",
        json={"message": "Chào bạn, bạn là ai?", "session_id": test_session, "top_k": 3},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

    chunks = []
    done_event = None

    for line in res.iter_lines():
        if line.startswith("data: "):
            payload_str = line[6:].strip()
            if not payload_str:
                continue
            payload = json.loads(payload_str)
            if "chunk" in payload:
                chunks.append(payload["chunk"])
            if payload.get("done") is True:
                done_event = payload

    assert len(chunks) > 0, "Expected at least 1 streamed chunk event"
    assert done_event is not None, "Expected terminal done event with full answer"
    assert "answer" in done_event
    assert "books" in done_event
    assert done_event["session_id"] == test_session


# -------------------------------------------------------------
# 3. RAG Retrieval & Source Grounding (book_203 The Pragmatic Programmer)
# -------------------------------------------------------------
def test_03_rag_retrieval_with_sources():
    test_session = f"test_rag_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/chat/message",
        json={
            "message": "Sách The Pragmatic Programmer có những tác giả nào và nội dung chính là gì?",
            "session_id": test_session,
            "top_k": 3,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["answer"]) > 0
    # Intent should be book_query
    assert data["intent"] in ["book_query", "small_talk", "library_info"]
    # If sources were returned, check structure
    if data["books"]:
        first_source = data["books"][0]
        assert "metadata" in first_source or "title" in first_source


# -------------------------------------------------------------
# 4. Anti-Hallucination & Out of Domain Handling
# -------------------------------------------------------------
def test_04_anti_hallucination_and_out_of_domain():
    test_session = f"test_ood_{uuid.uuid4().hex[:8]}"
    # Ask completely unrelated question
    res = client.post(
        "/api/v1/chat/message",
        json={
            "message": "Thời tiết ngày mai ở thủ đô Berlin của nước Đức ra sao?",
            "session_id": test_session,
            "top_k": 3,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    # Must NOT hallucinate book sources for unrelated questions
    assert data["intent"] == "out_of_domain" or len(data["books"]) == 0


# -------------------------------------------------------------
# 5. Chat History Persistence & Retrieval
# -------------------------------------------------------------
def test_05_chat_history_persistence():
    test_session = f"test_hist_{uuid.uuid4().hex[:8]}"
    # Send message
    res = client.post(
        "/api/v1/chat/message",
        json={"message": "Tôi đang tìm hiểu về thư viện", "session_id": test_session, "top_k": 2},
    )
    assert res.status_code == 200

    # Retrieve history
    hist_res = client.get(f"/api/v1/chat/history/{test_session}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["session_id"] == test_session
    messages = hist_data["messages"]
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Tôi đang tìm hiểu về thư viện"
    assert messages[1]["role"] == "assistant"


# -------------------------------------------------------------
# 6. Multiple Sequential Messages & Context Continuity
# -------------------------------------------------------------
def test_06_sequential_conversation_flow():
    test_session = f"test_seq_{uuid.uuid4().hex[:8]}"
    # Message 1
    res1 = client.post(
        "/api/v1/chat/message",
        json={"message": "Thư viện có sách nào về công nghệ không?", "session_id": test_session, "top_k": 2},
    )
    assert res1.status_code == 200

    # Message 2 in same session
    res2 = client.post(
        "/api/v1/chat/message",
        json={"message": "Cuốn đầu tiên có tác giả là ai?", "session_id": test_session, "top_k": 2},
    )
    assert res2.status_code == 200
    assert len(res2.json()["answer"]) > 0


# -------------------------------------------------------------
# 7. Vietnamese Diacritics & Unicode Handling
# -------------------------------------------------------------
def test_07_vietnamese_unicode_support():
    test_session = f"test_vn_{uuid.uuid4().hex[:8]}"
    vn_question = "Tôi muốn tìm một cuốn sách giúp rèn luyện tư duy logic, sự kiên nhẫn và kỹ năng giải quyết vấn đề."
    res = client.post(
        "/api/v1/chat/message",
        json={"message": vn_question, "session_id": test_session, "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["answer"]) > 0


# -------------------------------------------------------------
# 8. Request Validation & Error Containment
# -------------------------------------------------------------
def test_08_chat_validation_errors():
    # Empty message should be rejected with 422 Unprocessable Entity
    res_empty = client.post("/api/v1/chat/message", json={"message": "", "top_k": 3})
    assert res_empty.status_code == 422

    # Invalid top_k (e.g. > 10)
    res_topk = client.post("/api/v1/chat/message", json={"message": "Hi", "top_k": 999})
    assert res_topk.status_code == 422


# -------------------------------------------------------------
# 9. Cross-Account Privacy Isolation (User A vs User B vs Guest)
# -------------------------------------------------------------
def test_09_chat_cross_account_isolation():
    from backend.core.security import create_access_token
    from backend.routers.chat_router import _save_session_history

    user_a = f"usera_{uuid.uuid4().hex[:6]}"
    user_b = f"userb_{uuid.uuid4().hex[:6]}"
    session_a = f"sess_{uuid.uuid4().hex[:8]}"

    token_a = create_access_token(data={"sub": user_a, "role": "user"})
    token_b = create_access_token(data={"sub": user_b, "role": "user"})

    # User A creates a chat history
    _save_session_history(
        username=user_a,
        session_id=session_a,
        messages=[
            {"role": "user", "content": "Tin nhắn bảo mật của User A", "timestamp": "12:00"},
            {"role": "assistant", "content": "Phản hồi bảo mật", "timestamp": "12:00"},
        ],
    )

    # 1. User A can view their own session
    res_a = client.get(
        f"/api/v1/chat/history/{session_a}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    assert len(res_a.json()["messages"]) == 2

    # 2. User B CANNOT access User A's session -> 403 Forbidden
    res_b = client.get(
        f"/api/v1/chat/history/{session_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 403
    assert "quyền" in res_b.json().get("detail", "").lower()

    # 3. User B CANNOT hijack User A's session ID in chat message -> 403 Forbidden
    res_hijack = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"message": "Cố tình xâm nhập", "session_id": session_a},
    )
    assert res_hijack.status_code == 403

    # 4. Guest CANNOT access User A's session -> 403 Forbidden
    res_guest = client.get(f"/api/v1/chat/history/{session_a}")
    assert res_guest.status_code == 403


# -------------------------------------------------------------
# 10. Thread-Safe Concurrent History Writes
# -------------------------------------------------------------
def test_10_chat_concurrent_writes():
    import concurrent.futures
    from backend.routers.chat_router import _save_session_history, _load_session_history

    test_user = f"concur_{uuid.uuid4().hex[:6]}"
    session_id = f"sess_concur_{uuid.uuid4().hex[:8]}"

    def write_op(idx: int):
        msgs = [
            {"role": "user", "content": f"Message {idx}", "timestamp": "12:00"},
            {"role": "assistant", "content": f"Reply {idx}", "timestamp": "12:00"},
        ]
        _save_session_history(test_user, session_id, msgs)
        loaded = _load_session_history(test_user, session_id)
        return len(loaded)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_op, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All writes should complete without throwing exceptions
    assert len(results) == 10
    assert all(r == 2 for r in results)


# -------------------------------------------------------------
# 11. Streaming Early Disconnection / Socket Abort Simulation
# -------------------------------------------------------------
def test_11_chat_streaming_early_cancellation():
    test_session = f"test_cancel_{uuid.uuid4().hex[:8]}"

    # Simulate client reading only the first chunk and aborting
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"message": "Xin chào, hãy giới thiệu 5 cuốn sách hay nhất", "session_id": test_session},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data: "):
                # Client abruptly stops reading here
                break

    # Verify server is still completely responsive and session can be queried
    hist_res = client.get(f"/api/v1/chat/history/{test_session}")
    assert hist_res.status_code in [200, 404]


# -------------------------------------------------------------
# 12. Corrupted History JSON Resilience
# -------------------------------------------------------------
def test_12_chat_corrupted_json_handling():
    from backend.core.config import CHAT_HISTORY_DIR
    from backend.routers.chat_router import _load_session_history

    corrupt_session = f"corrupt_{uuid.uuid4().hex[:8]}"
    corrupt_file = CHAT_HISTORY_DIR / f"{corrupt_session}.json"
    corrupt_file.write_text("{invalid_json: true, unterminated", encoding="utf-8")

    try:
        # Should gracefully return empty list without throwing uncaught 500 error
        res = _load_session_history("guest", corrupt_session)
        assert res == []

        api_res = client.get(f"/api/v1/chat/history/{corrupt_session}")
        assert api_res.status_code == 200
        assert api_res.json()["messages"] == []
    finally:
        if corrupt_file.exists():
            corrupt_file.unlink()

