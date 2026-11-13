"""
Comprehensive Test Suite for Phase 3.4.1 - Backend Social Community Engine & APIs
Classified into:
- Unit Tests: Database WAL mode, pragma, migrations, online backup/restore, input validation.
- Real Integration Tests: Running on live FastAPI app, real SQLite database (data/social_community.db),
  real JWT auth tokens, real books CSV.
"""

import concurrent.futures
import os
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import COMMUNITY_DB_PATH
from backend.services.community_db import (
    create_connection,
    get_db,
    run_migrations,
    backup_database,
    restore_database,
)

client = TestClient(app)


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_authenticated_user(prefix: str = "user") -> tuple[str, str, dict[str, str]]:
    """Helper to create a fresh user and return (username, password, auth_headers)."""
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "CommunityPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return username, password, headers


def get_admin_headers() -> dict[str, str]:
    """Helper to login as existing admin and return auth_headers."""
    login_res = client.post("/api/v1/auth/login", json={"username": "cong1", "password": "123"})
    if login_res.status_code != 200:
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. UNIT TESTS: Database Engine, WAL Mode, Pragmas & Migrations
# ==============================================================================

def test_unit_db_wal_mode_and_foreign_keys():
    """Verify that every connection enforces foreign keys, WAL mode, and busy timeout."""
    conn = create_connection()
    try:
        # Check foreign keys
        fk_cur = conn.execute("PRAGMA foreign_keys;")
        assert fk_cur.fetchone()[0] == 1

        # Check WAL mode
        wal_cur = conn.execute("PRAGMA journal_mode;")
        mode = wal_cur.fetchone()[0].upper()
        assert mode == "WAL"

        # Check busy timeout
        bt_cur = conn.execute("PRAGMA busy_timeout;")
        timeout = bt_cur.fetchone()[0]
        assert timeout >= 5000
    finally:
        conn.close()


def test_unit_schema_migrations_version():
    """Verify that schema migrations apply idempotently and track version >= 1."""
    v = run_migrations()
    assert v >= 1

    with get_db() as conn:
        cur = conn.execute("SELECT version, description FROM schema_migrations ORDER BY version ASC;")
        rows = cur.fetchall()
        assert len(rows) >= 1
        assert rows[0]["version"] == 1


def test_unit_backup_and_restore_database(tmp_path):
    """Verify native online backup and restore without locking errors."""
    backup_file = backup_database(backup_dir=tmp_path)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # Test restoring into a temporary db
    temp_restore_db = tmp_path / "restored_community.db"
    ok = restore_database(backup_file, target_db_path=temp_restore_db)
    assert ok is True
    assert temp_restore_db.exists()

    # Verify restored db is readable
    restored_conn = create_connection(temp_restore_db)
    try:
        cur = restored_conn.execute("SELECT COUNT(*) FROM user_profiles;")
        assert cur.fetchone() is not None
    finally:
        restored_conn.close()


# ==============================================================================
# 2. REAL INTEGRATION TESTS: Reviews API
# ==============================================================================

def test_real_integration_crud_review():
    """Verify full CRUD lifecycle for book reviews."""
    username, _, headers = create_authenticated_user("reviewer")
    book_id = "book_001"

    # 1. Create Review
    create_payload = {
        "rating": 5,
        "title": "Tác phẩm kinh điển tuyệt vời",
        "content": "Cuốn sách này mở ra tư duy tài chính vô cùng thực tế và sâu sắc cho độc giả trẻ.",
        "contains_spoiler": False,
    }
    res_create = client.post(f"/api/v1/community/books/{book_id}/reviews", headers=headers, json=create_payload)
    assert res_create.status_code == 201
    rev_data = res_create.json()
    review_id = rev_data["id"]
    assert rev_data["username"] == username
    assert rev_data["rating"] == 5
    assert rev_data["title"] == create_payload["title"]

    # 2. Get Book Reviews (Public)
    res_list = client.get(f"/api/v1/community/books/{book_id}/reviews?page=1&page_size=10")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == review_id for r in list_data["reviews"])

    # 3. Get Review Detail
    res_detail = client.get(f"/api/v1/community/reviews/{review_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == review_id

    # 4. Update Review
    update_payload = {
        "rating": 4,
        "title": "Cập nhật: Nhận xét sau khi đọc lại",
        "content": "Nội dung sách vẫn rất hay nhưng có một vài chương hơi lặp lại ý.",
        "contains_spoiler": True,
    }
    res_update = client.put(f"/api/v1/community/reviews/{review_id}", headers=headers, json=update_payload)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["rating"] == 4
    assert updated_data["title"] == update_payload["title"]
    assert updated_data["contains_spoiler"] is True

    # 5. Delete Review
    res_delete = client.delete(f"/api/v1/community/reviews/{review_id}", headers=headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["success"] is True

    # Verify not found after delete
    res_after = client.get(f"/api/v1/community/reviews/{review_id}")
    assert res_after.status_code == 404


def test_real_integration_duplicate_review_blocked():
    """Verify that a user cannot submit more than 1 review per book."""
    username, _, headers = create_authenticated_user("dup_user")
    book_id = "book_002"

    payload1 = {
        "rating": 5,
        "title": "Bài nhận xét đầu tiên",
        "content": "Một cuốn sách rất đáng đọc trong đời.",
    }
    res1 = client.post(f"/api/v1/community/books/{book_id}/reviews", headers=headers, json=payload1)
    assert res1.status_code == 201

    payload2 = {
        "rating": 3,
        "title": "Cố tình đánh giá lần hai",
        "content": "Nội dung này phải bị chặn bởi hệ thống.",
    }
    res2 = client.post(f"/api/v1/community/books/{book_id}/reviews", headers=headers, json=payload2)
    assert res2.status_code == 400
    assert "đã đánh giá" in res2.json()["detail"].lower()


def test_real_integration_nonexistent_book_id_blocked():
    """Verify that reviewing a nonexistent book_id returns 404."""
    _, _, headers = create_authenticated_user("nonexist_book_user")
    payload = {
        "rating": 4,
        "title": "Sách không tồn tại",
        "content": "Bài viết trên một mã sách giả mạo.",
    }
    res = client.post("/api/v1/community/books/book_999999/reviews", headers=headers, json=payload)
    assert res.status_code == 404
    assert "không tìm thấy sách" in res.json()["detail"].lower()


# ==============================================================================
# 3. REAL INTEGRATION TESTS: Comments & Threaded Replies
# ==============================================================================

def test_real_integration_crud_comment_and_replies():
    """Verify root comments and nested replies."""
    author_user, _, author_headers = create_authenticated_user("rev_author")
    commenter_user, _, commenter_headers = create_authenticated_user("commenter")

    # Author creates review
    rev_res = client.post(
        "/api/v1/community/books/book_003/reviews",
        headers=author_headers,
        json={"rating": 5, "title": "Review xuất sắc", "content": "Nội dung review sách chi tiết và chất lượng."},
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Commenter posts root comment
    root_cmt_res = client.post(
        f"/api/v1/community/reviews/{review_id}/comments",
        headers=commenter_headers,
        json={"content": "Tôi hoàn toàn đồng ý với góc nhìn của bạn!"},
    )
    assert root_cmt_res.status_code == 201
    root_cmt_id = root_cmt_res.json()["id"]
    assert root_cmt_res.json()["parent_comment_id"] is None

    # Author replies to root comment
    reply_res = client.post(
        f"/api/v1/community/reviews/{review_id}/comments",
        headers=author_headers,
        json={"content": "Cảm ơn bạn đã đọc và chia sẻ cảm nghĩ!", "parent_comment_id": root_cmt_id},
    )
    assert reply_res.status_code == 201
    assert reply_res.json()["parent_comment_id"] == root_cmt_id

    # List comments
    list_res = client.get(f"/api/v1/community/reviews/{review_id}/comments")
    assert list_res.status_code == 200
    cmts = list_res.json()["comments"]
    assert len(cmts) >= 2

    # Commenter updates comment
    update_res = client.put(
        f"/api/v1/community/comments/{root_cmt_id}",
        headers=commenter_headers,
        json={"content": "Nội dung đã được chỉnh sửa bổ sung thêm ý."},
    )
    assert update_res.status_code == 200
    assert "chỉnh sửa" in update_res.json()["content"]

    # Delete comment
    del_res = client.delete(f"/api/v1/community/comments/{root_cmt_id}", headers=commenter_headers)
    assert del_res.status_code == 200


def test_real_integration_invalid_parent_comment_blocked():
    """Verify that replying to a nonexistent parent comment returns 404."""
    _, _, headers = create_authenticated_user("bad_reply_user")
    rev_res = client.post(
        "/api/v1/community/books/book_004/reviews",
        headers=headers,
        json={"rating": 5, "title": "Sách hay", "content": "Bài viết thảo luận sôi nổi về sách."},
    )
    review_id = rev_res.json()["id"]

    res = client.post(
        f"/api/v1/community/reviews/{review_id}/comments",
        headers=headers,
        json={"content": "Trả lời comment ma", "parent_comment_id": "cmt_nonexistent123"},
    )
    assert res.status_code == 404


# ==============================================================================
# 4. REAL INTEGRATION TESTS: Reactions (Like / Unlike & Self-Like Prevention)
# ==============================================================================

def test_real_integration_like_unlike_and_self_like_blocked():
    """Verify reaction mechanics, duplicate like blocking, and self-like prevention."""
    user_a, _, headers_a = create_authenticated_user("author_like")
    user_b, _, headers_b = create_authenticated_user("liker_b")

    # User A creates review
    rev_res = client.post(
        "/api/v1/community/books/book_005/reviews",
        headers=headers_a,
        json={"rating": 4, "title": "Đánh giá chi tiết", "content": "Cuốn sách có nhiều bài học quý giá."},
    )
    review_id = rev_res.json()["id"]

    # 1. User A tries to self-like -> Blocked 400
    self_like_res = client.post(
        "/api/v1/community/reactions",
        headers=headers_a,
        json={"target_type": "review", "target_id": review_id},
    )
    assert self_like_res.status_code == 400
    assert "tự thích" in self_like_res.json()["detail"].lower()

    # 2. User B likes User A's review -> Success 200
    like_res = client.post(
        "/api/v1/community/reactions",
        headers=headers_b,
        json={"target_type": "review", "target_id": review_id},
    )
    assert like_res.status_code == 200
    assert like_res.json()["liked"] is True
    assert like_res.json()["likes_count"] == 1

    # 3. User B likes again -> Duplicate blocked 400
    dup_like_res = client.post(
        "/api/v1/community/reactions",
        headers=headers_b,
        json={"target_type": "review", "target_id": review_id},
    )
    assert dup_like_res.status_code == 400
    assert "đã thích" in dup_like_res.json()["detail"].lower()

    # 4. User B unlikes -> Success 200, count decreases to 0
    unlike_res = client.delete(
        f"/api/v1/community/reactions?target_type=review&target_id={review_id}",
        headers=headers_b,
    )
    assert unlike_res.status_code == 200
    assert unlike_res.json()["liked"] is False
    assert unlike_res.json()["likes_count"] == 0

    # 5. User B unlikes again when not liked -> Blocked 400
    unlike_again = client.delete(
        f"/api/v1/community/reactions?target_type=review&target_id={review_id}",
        headers=headers_b,
    )
    assert unlike_again.status_code == 400


# ==============================================================================
# 5. REAL INTEGRATION TESTS: Authorization, RBAC, IDOR & Guest Restrictions
# ==============================================================================

def test_real_integration_guest_unauthorized():
    """Verify that guest callers are rejected with 401 on private community actions."""
    # Guest cannot create review
    res_rev = client.post("/api/v1/community/books/book_001/reviews", json={"rating": 5, "title": "t", "content": "c"})
    assert res_rev.status_code == 401

    # Guest cannot post comment
    res_cmt = client.post("/api/v1/community/reviews/rev_123/comments", json={"content": "hello"})
    assert res_cmt.status_code == 401

    # Guest cannot like
    res_rx = client.post("/api/v1/community/reactions", json={"target_type": "review", "target_id": "rev_123"})
    assert res_rx.status_code == 401


def test_real_integration_idor_forbidden_edit_delete():
    """Verify that User B cannot edit or delete User A's review or comment."""
    _, _, headers_a = create_authenticated_user("owner_user")
    _, _, headers_b = create_authenticated_user("attacker_user")

    # User A creates review
    rev_res = client.post(
        "/api/v1/community/books/book_001/reviews",
        headers=headers_a,
        json={"rating": 5, "title": "Bài viết của A", "content": "Nội dung bài viết thuộc bản quyền của User A."},
    )
    assert rev_res.status_code in (201, 400)
    if rev_res.status_code == 400:
        # User already reviewed book_001, fetch review_id
        list_res = client.get("/api/v1/community/books/book_001/reviews")
        review_id = list_res.json()["reviews"][0]["id"]
    else:
        review_id = rev_res.json()["id"]

    # User B tries to update User A's review -> 403 Forbidden
    attack_put = client.put(
        f"/api/v1/community/reviews/{review_id}",
        headers=headers_b,
        json={"title": "Hacked Title", "content": "Nội dung bị sửa đổi trái phép."},
    )
    assert attack_put.status_code == 403

    # User B tries to delete User A's review -> 403 Forbidden
    attack_del = client.delete(f"/api/v1/community/reviews/{review_id}", headers=headers_b)
    assert attack_del.status_code == 403


def test_real_integration_admin_can_delete_violating_content():
    """Verify that Admin can delete violating reviews or comments of any user."""
    _, _, headers_a = create_authenticated_user("violator_user")
    admin_headers = get_admin_headers()

    # User A creates review
    rev_res = client.post(
        "/api/v1/community/books/book_006/reviews",
        headers=headers_a,
        json={"rating": 1, "title": "Bài review vi phạm", "content": "Nội dung mang tính chất spam hoặc công kích."},
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Admin deletes User A's review -> Allowed 200
    admin_del = client.delete(f"/api/v1/community/reviews/{review_id}", headers=admin_headers)
    assert admin_del.status_code == 200
    assert admin_del.json()["success"] is True


# ==============================================================================
# 6. REAL INTEGRATION TESTS: User Profile Management
# ==============================================================================

def test_real_integration_user_profile_management():
    """Verify retrieving and updating user profile."""
    username, _, headers = create_authenticated_user("profile_tester")

    # 1. Get Initial Profile
    res_get = client.get(f"/api/v1/community/profile/{username}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["username"] == username

    # 2. Update Profile
    update_data = {
        "display_name": "Độc Giả Tri Thức",
        "avatar_url": "https://example.com/avatar.jpg",
        "bio": "Yêu thích sách kinh tế, công nghệ và phát triển bản thân.",
    }
    res_put = client.put("/api/v1/community/profile/me", headers=headers, json=update_data)
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["display_name"] == update_data["display_name"]
    assert put_data["bio"] == update_data["bio"]


# ==============================================================================
# 7. CONCURRENCY & RACE CONDITION TEST: Multi-User Concurrent Reactions
# ==============================================================================

def test_real_integration_concurrent_likes():
    """Verify atomic consistency under multiple concurrent users liking the same review."""
    _, _, author_headers = create_authenticated_user("concur_author")
    rev_res = client.post(
        "/api/v1/community/books/book_007/reviews",
        headers=author_headers,
        json={"rating": 5, "title": "Review kiểm thử tải", "content": "Nội dung phục vụ kiểm tra tương tác đồng thời."},
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Generate 5 distinct users
    user_headers_list = [create_authenticated_user(f"liker_{i}")[2] for i in range(5)]

    def do_like(headers):
        return client.post(
            "/api/v1/community/reactions",
            headers=headers,
            json={"target_type": "review", "target_id": review_id},
        )

    # Concurrently like
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(do_like, user_headers_list))

    # All 5 likes should succeed
    for r in results:
        assert r.status_code == 200

    # Verify review likes_count is exactly 5
    rev_detail = client.get(f"/api/v1/community/reviews/{review_id}")
    assert rev_detail.status_code == 200
    assert rev_detail.json()["likes_count"] == 5


# ==============================================================================
# 8. SECURITY & EDGE CASES: Limits Validation, SQL Injection Defense & Persistence
# ==============================================================================

def test_real_integration_input_limits_validation():
    """Verify bounds checking for title, content, comment, and rating."""
    _, _, headers = create_authenticated_user("limit_user")

    # Title too short (< 3)
    res_short_title = client.post(
        "/api/v1/community/books/book_001/reviews",
        headers=headers,
        json={"rating": 5, "title": "ab", "content": "Nội dung hợp lệ trên mười ký tự."},
    )
    assert res_short_title.status_code == 422  # Pydantic validation

    # Content too short (< 10)
    res_short_content = client.post(
        "/api/v1/community/books/book_001/reviews",
        headers=headers,
        json={"rating": 5, "title": "Tiêu đề hợp lệ", "content": "Ngắn"},
    )
    assert res_short_content.status_code == 422

    # Rating out of range (6)
    res_bad_rating = client.post(
        "/api/v1/community/books/book_001/reviews",
        headers=headers,
        json={"rating": 6, "title": "Tiêu đề hợp lệ", "content": "Nội dung hợp lệ trên mười ký tự."},
    )
    assert res_bad_rating.status_code == 422

    # Comment too long (> 1000)
    res_long_cmt = client.post(
        "/api/v1/community/reviews/rev_sample/comments",
        headers=headers,
        json={"content": "a" * 1005},
    )
    assert res_long_cmt.status_code in (404, 422)


def test_real_integration_sql_injection_defense():
    """Verify that SQL injection payloads are neutralized by parameterized queries."""
    _, _, headers = create_authenticated_user("sqli_tester")
    injection_payload = "'; DROP TABLE reviews; --"

    # Injected book_id
    res_inj = client.get(f"/api/v1/community/books/{injection_payload}/reviews")
    assert res_inj.status_code == 200
    assert res_inj.json()["total"] == 0

    # Ensure table reviews is still intact and queryable
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM reviews;")
        assert cur.fetchone() is not None


def test_real_integration_data_persistence_across_reconnect():
    """Verify that reviews and comments persist across database disconnections."""
    username, _, headers = create_authenticated_user("persist_user")
    rev_res = client.post(
        "/api/v1/community/books/book_008/reviews",
        headers=headers,
        json={"rating": 5, "title": "Kiểm tra lưu trữ bền vững", "content": "Dữ liệu phải tồn tại sau khi đóng kết nối."},
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Open fresh direct SQLite connection
    fresh_conn = create_connection()
    try:
        cur = fresh_conn.execute("SELECT id, title, rating FROM reviews WHERE id = ?;", (review_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["id"] == review_id
        assert row["rating"] == 5
    finally:
        fresh_conn.close()


