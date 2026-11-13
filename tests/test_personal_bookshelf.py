from __future__ import annotations

import os
import sys
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
from backend.core.security import create_access_token
from backend.core.config import BOOKSHELVES_DIR

client = TestClient(app)


# -------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------
@pytest.fixture
def user_a():
    username = f"user_a_{uuid.uuid4().hex[:6]}"
    token = create_access_token(data={"sub": username, "role": "user"})
    return {"username": username, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def user_b():
    username = f"user_b_{uuid.uuid4().hex[:6]}"
    token = create_access_token(data={"sub": username, "role": "user"})
    return {"username": username, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


# -------------------------------------------------------------
# 1. Guest Access Denied (401 Unauthorized)
# -------------------------------------------------------------
def test_01_guest_access_denied():
    # Guest cannot list bookshelf
    res_list = client.get("/api/v1/bookshelf")
    assert res_list.status_code == 401

    # Guest cannot add to bookshelf
    res_add = client.post("/api/v1/bookshelf", json={"book_id": "book_203", "status": "favorite"})
    assert res_add.status_code == 401

    # Guest cannot check bookshelf
    res_check = client.get("/api/v1/bookshelf/check/book_203")
    assert res_check.status_code == 401

    # Guest cannot delete
    res_del = client.delete("/api/v1/bookshelf/some_id")
    assert res_del.status_code == 401


# -------------------------------------------------------------
# 2. Add Book to Favorites (Yêu thích)
# -------------------------------------------------------------
def test_02_add_book_to_favorites(user_a):
    res = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_203", "status": "favorite"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["book_id"] == "book_203"
    assert data["status"] == "favorite"
    assert "book" in data
    assert data["book"]["title"] == "The Pragmatic Programmer"

    # Check bookshelf list
    res_list = client.get("/api/v1/bookshelf", headers=user_a["headers"])
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["book_id"] == "book_203"
    assert list_data["items"][0]["status"] == "favorite"


# -------------------------------------------------------------
# 3. Prevent Duplicate Entry (Cùng sách và trạng thái)
# -------------------------------------------------------------
def test_03_prevent_duplicate_entry(user_a):
    # Add first time
    res1 = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_204", "status": "favorite"},
    )
    assert res1.status_code == 201

    # Add second time with exact same status -> 400 Bad Request
    res2 = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_204", "status": "favorite"},
    )
    assert res2.status_code == 400
    assert "đã tồn tại" in res2.json().get("detail", "").lower()


# -------------------------------------------------------------
# 4. Change Reading Status (Đang đọc -> Đã đọc)
# -------------------------------------------------------------
def test_04_change_reading_status_and_progress(user_a):
    # Add book as currently reading
    res_add = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_205", "status": "reading", "progress_page": 15, "total_pages": 200},
    )
    assert res_add.status_code == 201
    item_id = res_add.json()["id"]

    # Update progress
    res_prog = client.put(
        f"/api/v1/bookshelf/{item_id}",
        headers=user_a["headers"],
        json={"progress_page": 50},
    )
    assert res_prog.status_code == 200
    assert res_prog.json()["progress_page"] == 50
    assert res_prog.json()["status"] == "reading"

    # Change status to completed
    res_comp = client.put(
        f"/api/v1/bookshelf/{item_id}",
        headers=user_a["headers"],
        json={"status": "completed", "progress_page": 200, "rating": 5},
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "completed"
    assert res_comp.json()["progress_page"] == 200
    assert res_comp.json()["rating"] == 5


# -------------------------------------------------------------
# 5. Remove Book From Shelf (Xóa sách khỏi tủ)
# -------------------------------------------------------------
def test_05_remove_book_from_shelf(user_a):
    # Add book
    res_add = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_206", "status": "reading"},
    )
    assert res_add.status_code == 201
    item_id = res_add.json()["id"]

    # Delete by item_id
    res_del = client.delete(f"/api/v1/bookshelf/{item_id}", headers=user_a["headers"])
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Check bookshelf is now empty of this item
    res_check = client.get("/api/v1/bookshelf/check/book_206", headers=user_a["headers"])
    assert res_check.status_code == 200
    assert res_check.json()["in_bookshelf"] is False

    # Delete non-existent returns 404
    res_del_404 = client.delete(f"/api/v1/bookshelf/{item_id}", headers=user_a["headers"])
    assert res_del_404.status_code == 404


# -------------------------------------------------------------
# 6. Cross-Account Privacy Isolation (User A vs User B)
# -------------------------------------------------------------
def test_06_cross_account_isolation(user_a, user_b):
    # User A adds book_207 to favorite
    res_a = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_207", "status": "favorite", "notes": "Ghi chú bí mật của User A"},
    )
    assert res_a.status_code == 201
    item_a_id = res_a.json()["id"]

    # User B checks their own bookshelf -> MUST BE EMPTY
    res_b_list = client.get("/api/v1/bookshelf", headers=user_b["headers"])
    assert res_b_list.status_code == 200
    assert res_b_list.json()["total"] == 0

    # User B checks book_207 -> NOT in user B's bookshelf
    res_b_check = client.get("/api/v1/bookshelf/check/book_207", headers=user_b["headers"])
    assert res_b_check.status_code == 200
    assert res_b_check.json()["in_bookshelf"] is False

    # User B attempts to delete User A's item -> 404 Not Found (isolated)
    res_b_del = client.delete(f"/api/v1/bookshelf/{item_a_id}", headers=user_b["headers"])
    assert res_b_del.status_code == 404

    # User B attempts to update User A's item -> 404 Not Found (isolated)
    res_b_put = client.put(
        f"/api/v1/bookshelf/{item_a_id}",
        headers=user_b["headers"],
        json={"notes": "User B hack"},
    )
    assert res_b_put.status_code == 404

    # User A's data remains intact
    res_a_check = client.get("/api/v1/bookshelf/check/book_207", headers=user_a["headers"])
    assert res_a_check.status_code == 200
    assert res_a_check.json()["in_bookshelf"] is True
    assert res_a_check.json()["items"][0]["notes"] == "Ghi chú bí mật của User A"


# -------------------------------------------------------------
# 7. Non-Existent Book Handled Safely (404 Not Found)
# -------------------------------------------------------------
def test_07_nonexistent_book_handling(user_a):
    res_bad = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_fake_99999", "status": "favorite"},
    )
    assert res_bad.status_code == 404
    assert "không tìm thấy" in res_bad.json().get("detail", "").lower()


# -------------------------------------------------------------
# 8. Filter by Status (favorite / reading / completed)
# -------------------------------------------------------------
def test_08_filter_bookshelf_by_status(user_a):
    # Add 1 favorite, 1 reading, 1 completed (using valid IDs: book_001, book_002, book_003)
    res1 = client.post("/api/v1/bookshelf", headers=user_a["headers"], json={"book_id": "book_001", "status": "favorite"})
    assert res1.status_code == 201
    res2 = client.post("/api/v1/bookshelf", headers=user_a["headers"], json={"book_id": "book_002", "status": "reading"})
    assert res2.status_code == 201
    res3 = client.post("/api/v1/bookshelf", headers=user_a["headers"], json={"book_id": "book_003", "status": "completed"})
    assert res3.status_code == 201

    # Filter favorite
    favs = client.get("/api/v1/bookshelf?status=favorite", headers=user_a["headers"]).json()
    assert all(it["status"] == "favorite" for it in favs["items"])
    assert any(it["book_id"] == "book_001" for it in favs["items"])

    # Filter reading
    reading = client.get("/api/v1/bookshelf?status=reading", headers=user_a["headers"]).json()
    assert all(it["status"] == "reading" for it in reading["items"])
    assert any(it["book_id"] == "book_002" for it in reading["items"])

    # Filter completed
    completed = client.get("/api/v1/bookshelf?status=completed", headers=user_a["headers"]).json()
    assert all(it["status"] == "completed" for it in completed["items"])
    assert any(it["book_id"] == "book_003" for it in completed["items"])


# -------------------------------------------------------------
# 9. Persistence Across Logout / New Token
# -------------------------------------------------------------
def test_09_persistence_across_sessions(user_a):
    # Add book_001 to user_a shelf first
    res_add = client.post(
        "/api/v1/bookshelf",
        headers=user_a["headers"],
        json={"book_id": "book_001", "status": "favorite"},
    )
    assert res_add.status_code == 201

    # Issue a new token for the same user (simulating re-login)
    new_token = create_access_token(data={"sub": user_a["username"], "role": "user"})
    new_headers = {"Authorization": f"Bearer {new_token}"}

    res = client.get("/api/v1/bookshelf", headers=new_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1
    assert any(it["book_id"] == "book_001" for it in res.json()["items"])
