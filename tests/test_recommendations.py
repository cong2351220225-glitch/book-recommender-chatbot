from __future__ import annotations

import json
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.security import create_access_token
from backend.core.config import RECOMMENDATIONS_DIR, BOOKSHELVES_DIR
from backend.services.recommendation_service import (
    sanitize_username,
    load_user_recommendation_data,
    save_user_recommendation_data,
    update_user_preferences,
    save_user_feedback,
    recommend_cold_start,
    recommend_for_user,
    recommend_continue_reading,
    recommend_similar_books,
    _apply_diversity_filter,
    RecommendationWeights,
)
from backend.routers.bookshelf_router import _save_user_bookshelf

client = TestClient(app)

# Helper test tokens
USER_A = "rec_test_user_a"
USER_B = "rec_test_user_b"

token_a = create_access_token(data={"sub": USER_A, "role": "user"})
headers_a = {"Authorization": f"Bearer {token_a}"}

token_b = create_access_token(data={"sub": USER_B, "role": "user"})
headers_b = {"Authorization": f"Bearer {token_b}"}


@pytest.fixture(autouse=True)
def cleanup_test_user_files():
    """Dọn dẹp các tệp tạm của test user trước và sau mỗi bài test."""
    def clean():
        for u in [USER_A, USER_B, "malicious_user"]:
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
# 1. Guest Cold Start
# ---------------------------------------------------------------------------
def test_01_guest_cold_start():
    """Khách chưa đăng nhập nhận được danh sách sách nổi bật, xếp hạng cao và đa dạng."""
    res = client.get("/api/v1/recommendations/for-you?limit=8")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 8
    assert len(data["recommendations"]) == 8
    assert data["is_personalized"] is False
    assert "nổi bật" in data["source_basis"].lower()

    # Kiểm tra các sách có score > 0 và có lý do
    for rec in data["recommendations"]:
        assert rec["book_id"]
        assert rec["title"]
        assert rec["rating"] >= 4.0
        assert "tiêu biểu" in rec["reason"].lower() or "đánh giá cao" in rec["reason"].lower()


# ---------------------------------------------------------------------------
# 2. User mới có Preferences
# ---------------------------------------------------------------------------
def test_02_new_user_with_preferences():
    """User mới cập nhật thể loại quan tâm -> nhận đúng sách theo thể loại đó."""
    # 1. Cập nhật preferences
    pref_payload = {
        "preferred_genres": ["Tâm lý - Kỹ năng sống"],
        "preferred_authors": ["James Clear"],
        "reading_goal": "Xây dựng thói quen tốt",
    }
    pref_res = client.post("/api/v1/recommendations/preferences", json=pref_payload, headers=headers_a)
    assert pref_res.status_code == 200
    p_data = pref_res.json()
    assert p_data["username"] == USER_A
    assert "Tâm lý - Kỹ năng sống" in p_data["preferred_genres"]

    # 2. Lấy gợi ý
    rec_res = client.get("/api/v1/recommendations/for-you?limit=5", headers=headers_a)
    assert rec_res.status_code == 200
    r_data = rec_res.json()
    assert r_data["is_personalized"] is True
    assert len(r_data["recommendations"]) == 5

    # Cuốn đầu tiên nên có lý do liên quan đến sở thích
    first_item = r_data["recommendations"][0]
    assert "sở thích" in first_item["reason"].lower() or "tâm lý" in first_item["reason"].lower() or first_item["score"] > 2.0


# ---------------------------------------------------------------------------
# 3. Recommendation dựa trên Bookshelf
# ---------------------------------------------------------------------------
def test_03_recommendation_based_on_bookshelf():
    """Gợi ý ưu tiên các sách tương đồng với sách trong Tủ sách yêu thích."""
    # Thêm cuốn Atomic Habits (book_001) vào tủ sách yêu thích của USER_A
    _save_user_bookshelf(USER_A, {
        "username": USER_A,
        "items": {
            "book_001": {
                "item_id": "fav_01",
                "book_id": "book_001",
                "statuses": ["favorite"],
                "added_at": "2026-11-02T10:00:00Z",
            }
        }
    })

    rec_res = client.get("/api/v1/recommendations/for-you?limit=5", headers=headers_a)
    assert rec_res.status_code == 200
    recs = rec_res.json()["recommendations"]

    # Cuốn book_001 (đang trong tủ) không được xuất hiện lại trong kết quả
    book_ids = [r["book_id"] for r in recs]
    assert "book_001" not in book_ids

    # Ít nhất một cuốn có lý do liên quan đến sách yêu thích hoặc cùng thể loại
    reasons = [r["reason"].lower() for r in recs]
    assert any("thể loại" in r or "quan tâm" in r for r in reasons)


# ---------------------------------------------------------------------------
# 4. Continue Reading
# ---------------------------------------------------------------------------
def test_04_continue_reading():
    """Gợi ý sách tương đồng với cuốn sách đang đọc dở (status=reading)."""
    # Khách không có token gọi -> 401
    guest_res = client.get("/api/v1/recommendations/continue-reading")
    assert guest_res.status_code == 401

    # Đặt book_002 vào trạng thái reading
    _save_user_bookshelf(USER_A, {
        "username": USER_A,
        "items": {
            "book_002": {
                "item_id": "read_01",
                "book_id": "book_002",
                "statuses": ["reading"],
                "added_at": "2026-11-02T11:00:00Z",
            }
        }
    })

    rec_res = client.get("/api/v1/recommendations/continue-reading?limit=4", headers=headers_a)
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert len(data["recommendations"]) > 0
    assert "mạch đọc" in data["recommendations"][0]["reason"].lower()


# ---------------------------------------------------------------------------
# 5. Dislike Filter
# ---------------------------------------------------------------------------
def test_05_dislike_filter():
    """Khi user Dislike một cuốn sách, cuốn sách đó không bao giờ xuất hiện lại."""
    # Lấy gợi ý ban đầu
    initial_res = client.get("/api/v1/recommendations/for-you?limit=5", headers=headers_a)
    first_book_id = initial_res.json()["recommendations"][0]["book_id"]

    # Gửi feedback Dislike
    fb_res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": first_book_id, "liked": False, "reason": "Không thích phong cách viết"},
        headers=headers_a,
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["liked"] is False

    # Lấy lại gợi ý -> Cuốn sách bị dislike phải biến mất
    after_res = client.get("/api/v1/recommendations/for-you?limit=5", headers=headers_a)
    new_ids = [r["book_id"] for r in after_res.json()["recommendations"]]
    assert first_book_id not in new_ids


# ---------------------------------------------------------------------------
# 6. Like Boost
# ---------------------------------------------------------------------------
def test_06_like_boost():
    """Khi user Like một cuốn sách, trạng thái liked được ghi nhận và tăng điểm."""
    target_book_id = "book_003"
    fb_res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": target_book_id, "liked": True, "reason": "Rất hay và truyền cảm hứng"},
        headers=headers_a,
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["liked"] is True

    # Kiểm tra dữ liệu lưu trữ
    data = load_user_recommendation_data(USER_A)
    assert data["feedback"][target_book_id]["liked"] is True


# ---------------------------------------------------------------------------
# 7. Cross Account Isolation
# ---------------------------------------------------------------------------
def test_07_cross_account_isolation():
    """User A và User B có sở thích và feedback độc lập, không rò rỉ dữ liệu."""
    # User A thích sách Kinh tế
    client.post(
        "/api/v1/recommendations/preferences",
        json={"preferred_genres": ["Kinh tế - Khởi nghiệp"]},
        headers=headers_a,
    )

    # User B thích sách Khoa học viễn tưởng
    client.post(
        "/api/v1/recommendations/preferences",
        json={"preferred_genres": ["Khoa học - Công nghệ"]},
        headers=headers_b,
    )

    # Đọc lại preferences của từng user
    res_a = client.get("/api/v1/recommendations/preferences", headers=headers_a).json()
    res_b = client.get("/api/v1/recommendations/preferences", headers=headers_b).json()

    assert "Kinh tế - Khởi nghiệp" in res_a["preferred_genres"]
    assert "Khoa học - Công nghệ" not in res_a["preferred_genres"]

    assert "Khoa học - Công nghệ" in res_b["preferred_genres"]
    assert "Kinh tế - Khởi nghiệp" not in res_b["preferred_genres"]


# ---------------------------------------------------------------------------
# 8. Path Traversal Prevention
# ---------------------------------------------------------------------------
def test_08_path_traversal_prevention():
    """Kiểm tra ngăn chặn Path Traversal với các ký tự độc hại."""
    malicious_inputs = ["../admin", "..\\root", "/etc/passwd", "user/secret", "user..name"]
    for bad_name in malicious_inputs:
        with pytest.raises(ValueError):
            sanitize_username(bad_name)

    # Thử gửi feedback với book_id chứa path traversal
    bad_res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "../evil_book", "liked": True},
        headers=headers_a,
    )
    assert bad_res.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 9. Performance Benchmark
# ---------------------------------------------------------------------------
def test_09_performance_benchmark():
    """Đảm bảo thời gian phản hồi của API /for-you dưới 200ms."""
    start_time = time.perf_counter()
    res = client.get("/api/v1/recommendations/for-you?limit=10", headers=headers_a)
    duration_ms = (time.perf_counter() - start_time) * 1000

    assert res.status_code == 200
    assert duration_ms < 200.0, f"API phản hồi chậm: {duration_ms:.2f}ms (yêu cầu < 200ms)"


# ---------------------------------------------------------------------------
# 10. API Contract Validation
# ---------------------------------------------------------------------------
def test_10_api_contract_validation():
    """Xác thực cấu trúc JSON trả về tuân thủ đầy đủ schema Pydantic."""
    res = client.get("/api/v1/recommendations/for-you?limit=3")
    assert res.status_code == 200
    data = res.json()

    # Kiểm tra top-level keys
    assert "total" in data
    assert "recommendations" in data
    assert "algorithm" in data
    assert "is_personalized" in data
    assert "source_basis" in data

    # Kiểm tra item keys
    for item in data["recommendations"]:
        assert "book_id" in item
        assert "title" in item
        assert "author" in item
        assert "genre" in item
        assert "rating" in item
        assert "score" in item
        assert "reason" in item
        assert "reason_type" in item


# ---------------------------------------------------------------------------
# 11. Hủy Dislike và Khôi phục sách
# ---------------------------------------------------------------------------
def test_11_cancel_dislike_restore():
    """Người dùng có thể hủy Dislike (reset về None) để sách có thể được gợi ý lại."""
    book_id = "book_005"

    # 1. Dislike
    client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": book_id, "liked": False},
        headers=headers_a,
    )
    data1 = load_user_recommendation_data(USER_A)
    assert data1["feedback"][book_id]["liked"] is False

    # 2. Reset / Hủy Dislike (liked = None)
    reset_res = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": book_id, "liked": None},
        headers=headers_a,
    )
    assert reset_res.status_code == 200
    data2 = load_user_recommendation_data(USER_A)
    assert book_id not in data2["feedback"]


# ---------------------------------------------------------------------------
# 12. Sách không tồn tại xử lý 404
# ---------------------------------------------------------------------------
def test_12_nonexistent_book_handling():
    """Truy vấn sách tương tự hoặc feedback với mã sách không tồn tại trả về 404."""
    res_similar = client.get("/api/v1/recommendations/similar/nonexistent_99999")
    assert res_similar.status_code == 404

    res_fb = client.post(
        "/api/v1/recommendations/feedback",
        json={"book_id": "nonexistent_99999", "liked": True},
        headers=headers_a,
    )
    assert res_fb.status_code == 404


# ---------------------------------------------------------------------------
# 13. Tự phục hồi khi file JSON bị hỏng
# ---------------------------------------------------------------------------
def test_13_corrupted_json_recovery():
    """Hệ thống tự phục hồi dữ liệu mặc định an toàn nếu file JSON cá nhân bị hỏng."""
    corrupted_file = RECOMMENDATIONS_DIR / f"{USER_A}.json"
    with open(corrupted_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json corrupted data ...")

    # Đọc lại không bị sập (crash 500) mà trả về default an toàn
    recovered = load_user_recommendation_data(USER_A)
    assert recovered["username"] == USER_A
    assert isinstance(recovered["preferences"], dict)


# ---------------------------------------------------------------------------
# 14. Kiểm tra đa dạng hóa thể loại (Anti-Monopoly)
# ---------------------------------------------------------------------------
def test_14_diversity_anti_monopoly():
    """Đảm bảo không một thể loại nào chiếm quá tỷ lệ tối đa nếu còn các thể loại khác."""
    mock_items = [
        {"book_id": f"b_{i}", "genre": "Kinh tế", "author": f"Author {i}", "score": 10.0 - i}
        for i in range(10)
    ]
    mock_items.extend([
        {"book_id": f"b_lit_{i}", "genre": "Văn học", "author": f"Lit Author {i}", "score": 5.0 - i}
        for i in range(10)
    ])
    mock_items.extend([
        {"book_id": f"b_sci_{i}", "genre": "Khoa học", "author": f"Sci Author {i}", "score": 3.0 - i}
        for i in range(10)
    ])

    filtered = _apply_diversity_filter(mock_items, limit=10, max_per_genre_ratio=0.4)
    assert len(filtered) == 10

    # Số lượng sách Kinh tế không được vượt quá max_per_genre (max(2, 10 * 0.4) = 4)
    kinhte_count = sum(1 for b in filtered if b["genre"] == "Kinh tế")
    assert kinhte_count <= 4
    assert any(b["genre"] == "Văn học" for b in filtered)
