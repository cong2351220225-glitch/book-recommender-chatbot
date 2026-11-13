from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import CHAT_HISTORY_DIR
from backend.core.security import create_access_token
from rag_engine import get_library_book_count

client = TestClient(app)


def test_scenario_1_to_5_chat_sessions_full_lifecycle():
    """Test 1: Tạo hai phiên, gửi nội dung khác nhau
    Test 2: Chuyển đổi và kiểm tra không bị trộn lẫn
    Test 3: Tái xác thực và kiểm tra tồn tại bền vững
    Test 4: Xóa một phiên và xác nhận phiên kia nguyên vẹn
    """
    username = f"test_reader_{uuid.uuid4().hex[:8]}"
    token = create_access_token({"sub": username})
    headers = {"Authorization": f"Bearer {token}"}

    sess_1 = f"sess_clean_code_{uuid.uuid4().hex[:6]}"
    sess_2 = f"sess_ai_{uuid.uuid4().hex[:6]}"

    # 1. Gửi câu hỏi vào phiên 1
    res1 = client.post(
        "/api/v1/chat/message",
        headers=headers,
        json={"message": "alo cho tôi hỏi về sách lập trình", "session_id": sess_1, "top_k": 3},
    )
    assert res1.status_code == 200

    # 2. Gửi câu hỏi vào phiên 2
    res2 = client.post(
        "/api/v1/chat/message",
        headers=headers,
        json={"message": "alo cho tôi hỏi về tâm lý học", "session_id": sess_2, "top_k": 3},
    )
    assert res2.status_code == 200

    # 3. Kiểm tra chuyển đổi qua lại: lịch sử không bị trộn lẫn
    hist1 = client.get(f"/api/v1/chat/history/{sess_1}", headers=headers)
    assert hist1.status_code == 200
    msgs1 = hist1.json()["messages"]
    assert any("lập trình" in m["content"] for m in msgs1)
    assert not any("tâm lý học" in m["content"] for m in msgs1)

    hist2 = client.get(f"/api/v1/chat/history/{sess_2}", headers=headers)
    assert hist2.status_code == 200
    msgs2 = hist2.json()["messages"]
    assert any("tâm lý học" in m["content"] for m in msgs2)
    assert not any("lập trình" in m["content"] for m in msgs2)

    # 4. Giả lập đăng nhập lại với token mới: Lịch sử vẫn còn nguyên
    new_token = create_access_token({"sub": username})
    new_headers = {"Authorization": f"Bearer {new_token}"}
    sessions_res = client.get("/api/v1/chat/sessions", headers=new_headers)
    assert sessions_res.status_code == 200
    session_list = sessions_res.json()["sessions"]
    s_ids = [s["id"] for s in session_list]
    assert sess_1 in s_ids
    assert sess_2 in s_ids

    # 5. Xóa session 1: session 2 không bị ảnh hưởng
    del_res = client.delete(f"/api/v1/chat/sessions/{sess_1}", headers=new_headers)
    assert del_res.status_code == 200

    # Kiểm tra lại danh sách
    sessions_after = client.get("/api/v1/chat/sessions", headers=new_headers).json()["sessions"]
    s_ids_after = [s["id"] for s in sessions_after]
    assert sess_1 not in s_ids_after
    assert sess_2 in s_ids_after

    # Session 2 vẫn đọc được bình thường
    hist2_after = client.get(f"/api/v1/chat/history/{sess_2}", headers=new_headers)
    assert hist2_after.status_code == 200
    assert len(hist2_after.json()["messages"]) > 0

    # Dọn dẹp session 2
    client.delete(f"/api/v1/chat/sessions/{sess_2}", headers=new_headers)


def test_scenario_6_and_7_top_k_execution():
    """Test 6 & 7: Kiểm tra Top-K = 1, 5, 10 thực sự được truyền đến Backend và RAG Engine."""
    with patch("backend.routers.chat_router.handle_user_message") as mock_rag:
        mock_rag.return_value = ("Gợi ý sách mẫu", [{"id": "book1", "title": "Sách 1"}], "book_query")

        for test_k in [1, 5, 10]:
            res = client.post(
                "/api/v1/chat/message",
                json={
                    "message": "Gợi ý sách lập trình hay nhất",
                    "top_k": test_k,
                    "session_id": f"sess_k_{test_k}",
                },
            )
            assert res.status_code == 200
            # Kiểm tra handle_user_message nhận đúng top_k
            mock_rag.assert_called()
            call_kwargs = mock_rag.call_args[1] if mock_rag.call_args[1] else {}
            call_args = mock_rag.call_args[0]
            # top_k là argument thứ 2 hoặc kwargs
            passed_top_k = call_kwargs.get("top_k", call_args[1] if len(call_args) > 1 else None)
            assert passed_top_k == test_k, f"Backend passed {passed_top_k} instead of {test_k}"


def test_scenario_8_vector_count_chroma_alignment():
    """Test 8: Đối chiếu số vector hiển thị với ChromaDB thực tế."""
    real_chroma_count = get_library_book_count()
    assert real_chroma_count == 208

    res = client.get("/api/v1/chat/config")
    assert res.status_code == 200
    data = res.json()
    assert data["vector_count"] == real_chroma_count
    assert data["vector_count"] == 208


def test_scenario_9_error_handling_when_backend_chroma_fails():
    """Test 9: Xử lý lỗi khi ChromaDB gặp sự cố, đảm bảo endpoint không crash 500."""
    with patch("backend.routers.chat_router.get_library_book_count", side_effect=RuntimeError("ChromaDB connection lost")):
        res = client.get("/api/v1/chat/config")
        assert res.status_code == 200
        data = res.json()
        assert data["vector_count"] == 0

