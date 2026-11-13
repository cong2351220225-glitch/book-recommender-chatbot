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

client = TestClient(app)


# -------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------
@pytest.fixture
def user_a():
    username = f"reader_a_{uuid.uuid4().hex[:6]}"
    token = create_access_token(data={"sub": username, "role": "user"})
    return {"username": username, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def user_b():
    username = f"reader_b_{uuid.uuid4().hex[:6]}"
    token = create_access_token(data={"sub": username, "role": "user"})
    return {"username": username, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


# -------------------------------------------------------------
# 1. Open Valid PDF Document (book_203)
# -------------------------------------------------------------
def test_01_open_valid_pdf_document():
    # 1. Check status
    res_status = client.get("/api/v1/reading/status/book_203")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["can_read_locally"] is True
    assert status_data["reading_type"] == "pdf"
    assert "/api/v1/reading/file/book_203" in status_data["reading_url"]

    # 2. Get file stream
    res_file = client.get("/api/v1/reading/file/book_203")
    assert res_file.status_code == 200
    assert "application/pdf" in res_file.headers.get("content-type", "")
    assert res_file.headers.get("accept-ranges") == "bytes"
    # Verify PDF signature (%PDF-)
    content = res_file.content
    assert content.startswith(b"%PDF-")
    assert len(content) > 500


# -------------------------------------------------------------
# 2. Non-Existent Document (404 Not Found)
# -------------------------------------------------------------
def test_02_nonexistent_document_handling():
    res = client.get("/api/v1/reading/file/book_fake_99999")
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()


# -------------------------------------------------------------
# 3. Path Traversal & Security Attack Prevention (400 / 404)
# -------------------------------------------------------------
def test_03_path_traversal_prevention():
    from backend.routers.reading_router import _sanitize_book_id
    from reading_service import validate_local_file
    from fastapi import HTTPException

    # 1. API endpoint rejects bad/traversal IDs with 400 or 404
    malicious_ids = [
        "..%2F..%2Fetc%2Fpasswd",
        "..%5C..%5Cwindows%5Csystem32",
        "book%203; rm -rf",
        "book_203%00.pdf",
    ]
    for bad_id in malicious_ids:
        res = client.get(f"/api/v1/reading/file/{bad_id}")
        assert res.status_code in [400, 404], f"Expected 400/404 for {bad_id}, got {res.status_code}"

    # 2. Direct service unit check: validate_local_file blocks traversal
    assert validate_local_file("../../secret.txt") is None
    assert validate_local_file("..\\..\\windows\\system32") is None
    assert validate_local_file("C:\\Windows\\System32\\cmd.exe") is None
    assert validate_local_file("/etc/passwd") is None

    # 3. Direct router sanitizer check raises HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        _sanitize_book_id("../../secret")
    assert exc_info.value.status_code == 400


# -------------------------------------------------------------
# 4. Unauthorized Access Rejection (Guest blocked on Progress)
# -------------------------------------------------------------
def test_04_unauthorized_progress_rejection():
    # Guest cannot save reading progress
    res_post = client.post(
        "/api/v1/reading/progress",
        json={"book_id": "book_203", "current_page": 5, "total_pages": 100},
    )
    assert res_post.status_code == 401

    # Guest cannot get private reading progress
    res_get = client.get("/api/v1/reading/progress/book_203")
    assert res_get.status_code == 401


# -------------------------------------------------------------
# 5. Reading Document Metadata Info Endpoint
# -------------------------------------------------------------
def test_05_reading_document_info(user_a):
    res = client.get("/api/v1/reading/info/book_203", headers=user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == "book_203"
    assert data["title"] == "The Pragmatic Programmer"
    assert data["can_read"] is True
    assert data["format"] == "pdf"
    assert data["file_size_bytes"] > 0
    assert "/api/v1/reading/file/book_203" in data["file_url"]


# -------------------------------------------------------------
# 6. Save and Restore Reading Position
# -------------------------------------------------------------
def test_06_save_and_restore_reading_position(user_a):
    # Save reading progress: page 3 of 5 (60%)
    res_save = client.post(
        "/api/v1/reading/progress",
        headers=user_a["headers"],
        json={
            "book_id": "book_203",
            "current_page": 3,
            "total_pages": 5,
            "last_read_location": "Chương 1: Triết lý thực dụng",
        },
    )
    assert res_save.status_code == 200
    save_data = res_save.json()
    assert save_data["current_page"] == 3
    assert save_data["total_pages"] == 5
    assert save_data["progress_percent"] == 60.0
    assert "Chương 1" in save_data["last_read_location"]

    # Restore reading progress
    res_get = client.get("/api/v1/reading/progress/book_203", headers=user_a["headers"])
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["current_page"] == 3
    assert get_data["total_pages"] == 5
    assert get_data["progress_percent"] == 60.0


# -------------------------------------------------------------
# 7. Sync with Personal Bookshelf (Phase 3.2.1 Integration)
# -------------------------------------------------------------
def test_07_sync_with_personal_bookshelf(user_a):
    # Save reading progress
    res_save = client.post(
        "/api/v1/reading/progress",
        headers=user_a["headers"],
        json={"book_id": "book_203", "current_page": 3, "total_pages": 5},
    )
    assert res_save.status_code == 200

    # Reading progress saved should automatically sync to bookshelf!
    shelf_res = client.get("/api/v1/bookshelf", headers=user_a["headers"])
    assert shelf_res.status_code == 200
    items = shelf_res.json()["items"]
    # Check book_203 exists in bookshelf with progress_page == 3
    matching = [it for it in items if it["book_id"] == "book_203"]
    assert len(matching) >= 1
    assert matching[0]["progress_page"] == 3
    assert matching[0]["total_pages"] == 5


# -------------------------------------------------------------
# 8. Cross-Account Reading Isolation (User A vs User B)
# -------------------------------------------------------------
def test_08_cross_account_reading_isolation(user_a, user_b):
    # User A saves progress at page 4
    client.post(
        "/api/v1/reading/progress",
        headers=user_a["headers"],
        json={"book_id": "book_203", "current_page": 4, "total_pages": 5},
    )

    # User B has not read book_203 yet -> should get default starting page 1
    res_b = client.get("/api/v1/reading/progress/book_203", headers=user_b["headers"])
    assert res_b.status_code == 200
    assert res_b.json()["current_page"] == 1
    assert res_b.json()["progress_percent"] == 0.0


# -------------------------------------------------------------
# 9. Resume Reading Across Logout & Re-login
# -------------------------------------------------------------
def test_09_resume_across_sessions(user_a):
    # Save progress for user_a
    client.post(
        "/api/v1/reading/progress",
        headers=user_a["headers"],
        json={"book_id": "book_203", "current_page": 4, "total_pages": 5},
    )

    # Issue a new token simulating logout and re-login
    new_token = create_access_token(data={"sub": user_a["username"], "role": "user"})
    new_headers = {"Authorization": f"Bearer {new_token}"}

    res = client.get("/api/v1/reading/progress/book_203", headers=new_headers)
    assert res.status_code == 200
    assert res.json()["current_page"] == 4
    assert res.json()["total_pages"] == 5
