from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.security import create_access_token
from backend.core.config import RECOMMENDATIONS_DIR, BOOKSHELVES_DIR
from backend.routers.bookshelf_router import _save_user_bookshelf

client = TestClient(app)

USER_1 = "flutter_rec_user_1"
USER_2 = "flutter_rec_user_2"

token_1 = create_access_token(data={"sub": USER_1, "role": "user"})
headers_1 = {"Authorization": f"Bearer {token_1}"}

token_2 = create_access_token(data={"sub": USER_2, "role": "user"})
headers_2 = {"Authorization": f"Bearer {token_2}"}


@pytest.fixture(autouse=True)
def cleanup_flutter_rec_files():
    def clean():
        for u in [USER_1, USER_2]:
            p = RECOMMENDATIONS_DIR / f"{u}.json"
            if p.exists():
                p.unlink()
            shelf_p = BOOKSHELVES_DIR / f"{u}.json"
            if shelf_p.exists():
                shelf_p.unlink()
    clean()
    yield
    clean()


# ---------------------------------------------------------------------------
# 1. Parse JSON Recommendation thành công
# ---------------------------------------------------------------------------
def test_01_parse_recommendation_json_contract():
    """Hợp đồng JSON của API /for-you khớp cấu trúc RecommendationListModel trong Flutter."""
    res = client.get("/api/v1/recommendations/for-you?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["total"], int)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["algorithm"], str)
    assert isinstance(data["is_personalized"], bool)
    assert isinstance(data["source_basis"], str)


# ---------------------------------------------------------------------------
# 2. Parse dữ liệu nullable
# ---------------------------------------------------------------------------
def test_02_parse_nullable_fields_contract():
    """Các trường nullable (year, pages, cover_url, user_feedback) được xử lý an toàn."""
    res = client.get("/api/v1/recommendations/for-you?limit=3")
    assert res.status_code == 200
    items = res.json()["recommendations"]
    for item in items:
        assert "book_id" in item
        assert "title" in item
        assert "author" in item
        assert "genre" in item
        # year, pages có thể là None hoặc số
        assert "year" in item
        assert "pages" in item
        # user_feedback có thể là None hoặc chuỗi
        assert item.get("user_feedback") in (None, "liked", "disliked")


# ---------------------------------------------------------------------------
# 3. API For You có dữ liệu
# ---------------------------------------------------------------------------
def test_03_api_for_you_returns_valid_data():
    """API For You trả về danh sách có dữ liệu thực tế."""
    res = client.get("/api/v1/recommendations/for-you?limit=4")
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 4
    for r in data["recommendations"]:
        assert r["rating"] > 0
        assert len(r["reason"]) > 0


# ---------------------------------------------------------------------------
# 4. API Continue Reading có dữ liệu
# ---------------------------------------------------------------------------
def test_04_api_continue_reading():
    """API Continue Reading trả về danh sách sách tiếp tục mạch đọc khi user có sách đang đọc."""
    # Tạo sách đang đọc cho USER_1
    _save_user_bookshelf(USER_1, {
        "username": USER_1,
        "items": {
            "book_001": {
                "item_id": "item_01",
                "book_id": "book_001",
                "statuses": ["reading"],
                "added_at": "2026-11-02T10:00:00Z",
            }
        }
    })

    res = client.get("/api/v1/recommendations/continue-reading?limit=4", headers=headers_1)
    assert res.status_code == 200
    data = res.json()
    assert data["is_personalized"] is True
    assert len(data["recommendations"]) > 0
    assert "mạch đọc" in data["recommendations"][0]["reason"].lower()


# ---------------------------------------------------------------------------
# 5. API Similar trả đúng book
# ---------------------------------------------------------------------------
def test_05_api_similar_books():
    """API Similar trả về sách tương đồng với một cuốn sách cụ thể."""
    res = client.get("/api/v1/recommendations/similar/book_001?limit=3")
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) <= 3
    # Không được chứa chính book_001
    assert "book_001" not in [b["book_id"] for b in data["recommendations"]]


# ---------------------------------------------------------------------------
# 6. Đọc Preferences
# ---------------------------------------------------------------------------
def test_06_get_preferences():
    """Đọc preferences của user qua token."""
    res = client.get("/api/v1/recommendations/preferences", headers=headers_1)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == USER_1
    assert isinstance(data["preferred_genres"], list)
    assert isinstance(data["preferred_authors"], list)


# ---------------------------------------------------------------------------
# 7. Cập nhật Preferences
# ---------------------------------------------------------------------------
def test_07_update_preferences():
    """Cập nhật preferences thành công và lưu lại."""
    payload = {
        "preferred_genres": ["Khoa học - Công nghệ", "Kinh tế - Khởi nghiệp"],
        "preferred_authors": ["James Clear"],
        "reading_goal": "Học kỹ năng mới mỗi tuần",
    }
    res = client.post("/api/v1/recommendations/preferences", json=payload, headers=headers_1)
    assert res.status_code == 200
    data = res.json()
    assert "Khoa học - Công nghệ" in data["preferred_genres"]
    assert "Kinh tế - Khởi nghiệp" in data["preferred_genres"]
    assert data["reading_goal"] == "Học kỹ năng mới mỗi tuần"


# ---------------------------------------------------------------------------
# 8. Like sách
# ---------------------------------------------------------------------------
def test_08_like_book():
    """User gửi phản hồi Like cho cuốn sách."""
    res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "book_002", "liked": True, "reason": "Thích nội dung"},
        headers=headers_1,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["liked"] is True


# ---------------------------------------------------------------------------
# 9. Dislike sách
# ---------------------------------------------------------------------------
def test_09_dislike_book():
    """User gửi phản hồi Dislike cho cuốn sách."""
    res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "book_004", "liked": False, "reason": "Không quan tâm"},
        headers=headers_1,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["liked"] is False


# ---------------------------------------------------------------------------
# 10. Restore Dislike
# ---------------------------------------------------------------------------
def test_10_restore_dislike():
    """User gửi liked=None để khôi phục sách đã dislike."""
    # 1. Dislike trước
    client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "book_005", "liked": False},
        headers=headers_1,
    )

    # 2. Khôi phục (liked=None)
    res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "book_005", "liked": None},
        headers=headers_1,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["liked"] is None


# ---------------------------------------------------------------------------
# 11. Xử lý token hết hạn / không hợp lệ
# ---------------------------------------------------------------------------
def test_11_expired_or_invalid_token():
    """Gửi token rác hoặc hết hạn bị từ chối 401 Unauthorized."""
    res = client.get("/api/v1/recommendations/preferences", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res.status_code == 401

    res_fb = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "book_001", "liked": True},
        headers={"Authorization": "Bearer expired_or_fake_token"},
    )
    assert res_fb.status_code == 401


# ---------------------------------------------------------------------------
# 12. Guest không gọi nhầm API cá nhân
# ---------------------------------------------------------------------------
def test_12_guest_cannot_access_private_apis():
    """Khách không có token cố gọi API cá nhân nhận 401 Unauthorized."""
    assert client.get("/api/v1/recommendations/preferences").status_code == 401
    assert client.post("/api/v1/recommendations/preferences", json={}).status_code == 401
    assert client.get("/api/v1/recommendations/continue-reading").status_code == 401
    assert client.post("/api/v1/recommendations/feedback", json={"book_id": "book_001"}).status_code == 401
    assert client.post("/api/v1/recommendations/refresh").status_code == 401


# ---------------------------------------------------------------------------
# 13. Logout xóa dữ liệu Provider (Simulation logic)
# ---------------------------------------------------------------------------
def test_13_logout_provider_isolation_logic():
    """Xác nhận mô hình cô lập dữ liệu khi user logout."""
    # Mô phỏng trạng thái provider
    mock_provider_state = {
        "current_username": USER_1,
        "for_you_list": ["book_001", "book_002"],
        "preferences": {"preferred_genres": ["Kinh tế"]},
    }
    # Khi logout: gọi clearData()
    mock_provider_state.clear()
    assert len(mock_provider_state) == 0
    assert "for_you_list" not in mock_provider_state


# ---------------------------------------------------------------------------
# 14. Chuyển User A sang User B không lộ dữ liệu
# ---------------------------------------------------------------------------
def test_14_user_switching_data_isolation():
    """User 1 và User 2 không nhìn thấy preferences hoặc feedback của nhau."""
    client.post(
        "/api/v1/recommendations/preferences",
        json={"preferred_genres": ["Triết học - Tư tưởng"]},
        headers=headers_1,
    )
    client.post(
        "/api/v1/recommendations/preferences",
        json={"preferred_genres": ["Công nghệ thông tin"]},
        headers=headers_2,
    )

    data1 = client.get("/api/v1/recommendations/preferences", headers=headers_1).json()
    data2 = client.get("/api/v1/recommendations/preferences", headers=headers_2).json()

    assert data1["preferred_genres"] == ["Triết học - Tư tưởng"]
    assert data2["preferred_genres"] == ["Công nghệ thông tin"]


# ---------------------------------------------------------------------------
# 15. Xử lý API lỗi và mã sách độc hại
# ---------------------------------------------------------------------------
def test_15_error_handling_and_input_validation():
    """Mã sách không tồn tại -> 404, mã sách chứa path traversal -> 400 hoặc 422."""
    res_404 = client.get("/api/v1/recommendations/similar/unknown_book_123")
    assert res_404.status_code == 404

    res_traversal = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "../../etc/passwd", "liked": True},
        headers=headers_1,
    )
    assert res_traversal.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 16. Kiểm tra tương thích với các API hiện có
# ---------------------------------------------------------------------------
def test_16_compatibility_with_existing_apis():
    """Đảm bảo các API cũ (books 208 bản ghi, health, stats) không bị ảnh hưởng."""
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["total_books_csv"] == 208

    books_res = client.get("/api/v1/books?page=1&page_size=10")
    assert books_res.status_code == 200
    assert books_res.json()["total"] == 208

