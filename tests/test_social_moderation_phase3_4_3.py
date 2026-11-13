"""
Comprehensive Test Suite for Phase 3.4.3 - Social Community Moderation & Reporting
Covers all 20 required scenarios:
1. Valid Review reporting by user
2. Valid Comment reporting by user
3. Block reporting nonexistent content (404)
4. Block self-reporting own content (400)
5. Block duplicate pending/reviewing reports by same user (409)
6. Block regular users from Admin APIs (403)
7. Admin list reports with filtering and breakdown
8. Admin view report detail with target snippet and history
9. Admin claim report (pending -> reviewing)
10. Admin dismiss report with notes (pending/reviewing -> dismissed)
11. Admin hide Review and verify it disappears from public listing
12. Admin hide Comment and verify it disappears from comments list
13. Admin delete content (soft delete)
14. Moderation action log recorded accurately in transaction
15. Reporter identity not leaked to regular users
16. Moderation action log cannot be modified or deleted via public API
17. Activity Feed does not display hidden or deleted reviews
18. Concurrent Admin handling (race condition on claim / action)
19. Multiple reports pointing to the same content resolved together
20. Migration v3 idempotency and schema verification on test database
"""

from __future__ import annotations

import concurrent.futures
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.community_db import get_db, run_migrations, create_connection
from backend.services import community_service

client = TestClient(app)


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_user(prefix: str = "mod_user") -> tuple[str, dict[str, str]]:
    """Helper to create a fresh user and return (username, auth_headers)."""
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "CommunityPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return username, {"Authorization": f"Bearer {token}"}


def get_admin_headers() -> dict[str, str]:
    """Helper to login as an admin account and return auth headers."""
    login_res = client.post("/api/v1/auth/login", json={"username": "cong1", "password": "123"})
    if login_res.status_code != 200:
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Test Cases 1-20
# ==============================================================================

def test_01_user_report_valid_review():
    """1. User submits a valid report for an infringing review."""
    author, auth_headers = create_user("author")
    reporter, rep_headers = create_user("reporter")

    # Author creates a review
    rev_res = client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 1, "title": "Offensive Review", "content": "This review contains spam and offensive words", "contains_spoiler": False},
        headers=auth_headers,
    )
    assert rev_res.status_code == 201
    rev_id = rev_res.json()["id"]

    # Reporter reports the review
    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "spam", "description": "Spam promotional link found"},
        headers=rep_headers,
    )
    assert rep_res.status_code == 201
    data = rep_res.json()
    assert data["target_type"] == "review"
    assert data["target_id"] == rev_id
    assert data["reason"] == "spam"
    assert data["status"] == "pending"
    assert data["reporter_username"] == reporter


def test_02_user_report_valid_comment():
    """2. User submits a valid report for an infringing comment."""
    author, auth_headers = create_user("rev_author")
    commenter, comm_headers = create_user("commenter")
    reporter, rep_headers = create_user("comm_reporter")

    # Author creates review
    rev_res = client.post(
        "/api/v1/community/books/book_002/reviews",
        json={"rating": 4, "title": "Good book", "content": "Very nice book to read on weekends", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    # Commenter creates comment
    comm_res = client.post(
        f"/api/v1/community/reviews/{rev_id}/comments",
        json={"content": "Harassing comment with abusive words"},
        headers=comm_headers,
    )
    assert comm_res.status_code == 201
    comm_id = comm_res.json()["id"]

    # Reporter reports the comment
    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "comment", "target_id": comm_id, "reason": "harassment", "description": "Abusive harassment"},
        headers=rep_headers,
    )
    assert rep_res.status_code == 201
    assert rep_res.json()["status"] == "pending"


def test_03_block_reporting_nonexistent_content():
    """3. Block reporting nonexistent review or comment with 404."""
    _, rep_headers = create_user("rep_404")

    # Nonexistent review
    res_rev = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": "rev_ghost_9999", "reason": "spam"},
        headers=rep_headers,
    )
    assert res_rev.status_code == 404

    # Nonexistent comment
    res_comm = client.post(
        "/api/v1/community/reports",
        json={"target_type": "comment", "target_id": "comm_ghost_9999", "reason": "harassment"},
        headers=rep_headers,
    )
    assert res_comm.status_code == 404


def test_04_block_self_reporting_own_content():
    """4. Block user from reporting their own content with 400 Bad Request."""
    user, headers = create_user("self_rep")

    # Create own review
    rev_res = client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 3, "title": "My own review", "content": "Just an ordinary review by myself", "contains_spoiler": False},
        headers=headers,
    )
    rev_id = rev_res.json()["id"]

    # Attempt to report own review
    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "spam"},
        headers=headers,
    )
    assert rep_res.status_code == 400
    assert "chính mình" in rep_res.json()["detail"].lower()


def test_05_block_duplicate_pending_reports():
    """5. Block duplicate reports while previous report is still pending/reviewing (409 Conflict)."""
    author, auth_headers = create_user("author_dup")
    reporter, rep_headers = create_user("reporter_dup")

    rev_res = client.post(
        "/api/v1/community/books/book_003/reviews",
        json={"rating": 2, "title": "Review for Dup Test", "content": "Testing duplicate reporting logic", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    # First report OK
    r1 = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "spam"},
        headers=rep_headers,
    )
    assert r1.status_code == 201

    # Second report by same reporter while first is pending -> 409 Conflict
    r2 = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "inappropriate"},
        headers=rep_headers,
    )
    assert r2.status_code == 409
    assert "đang được xem xét" in r2.json()["detail"].lower()


def test_06_block_regular_user_from_admin_apis():
    """6. Ensure regular users cannot call Admin Moderation APIs (403 Forbidden)."""
    _, user_headers = create_user("regular_user")

    # List reports
    r1 = client.get("/api/v1/community/admin/reports", headers=user_headers)
    assert r1.status_code == 403

    # Report detail
    r2 = client.get("/api/v1/community/admin/reports/rep_123", headers=user_headers)
    assert r2.status_code == 403

    # Claim report
    r3 = client.post("/api/v1/community/admin/reports/rep_123/claim", headers=user_headers)
    assert r3.status_code == 403

    # Dismiss report
    r4 = client.post("/api/v1/community/admin/reports/rep_123/dismiss", json={"notes": "dismiss"}, headers=user_headers)
    assert r4.status_code == 403

    # Actions
    r5 = client.post("/api/v1/community/admin/reports/rep_123/actions", json={"action": "hide", "reason": "bad"}, headers=user_headers)
    assert r5.status_code == 403

    # Moderation actions log
    r6 = client.get("/api/v1/community/admin/moderation-actions", headers=user_headers)
    assert r6.status_code == 403


def test_07_admin_list_reports_with_filtering_and_counts():
    """7. Admin lists reports with status filter, target_type filter, and status breakdown."""
    admin_headers = get_admin_headers()

    res = client.get("/api/v1/community/admin/reports?status=pending&page=1&page_size=10", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "status_counts" in data
    assert "pending" in data["status_counts"]
    assert "items" in data
    assert all(it["status"] == "pending" for it in data["items"])


def test_08_admin_view_report_detail():
    """8. Admin views report detail including target content, author, and history."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("dt_author")
    reporter, rep_headers = create_user("dt_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_004/reviews",
        json={"rating": 1, "title": "Detail Test Title", "content": "Detail test content 10+ characters", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "misinformation", "description": "Misleading info"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Admin inspects detail
    det_res = client.get(f"/api/v1/community/admin/reports/{rep_id}", headers=admin_headers)
    assert det_res.status_code == 200
    data = det_res.json()
    assert data["id"] == rep_id
    assert "Detail Test Title" in data["target_content"]
    assert data["target_author_username"] == author
    assert data["reporter_username"] == reporter
    assert "history" in data


def test_09_admin_claim_report():
    """9. Admin claims report: transitions status from pending to reviewing."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("claim_author")
    reporter, rep_headers = create_user("claim_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_005/reviews",
        json={"rating": 1, "title": "Claim Test Title", "content": "Content to test claim transition", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "inappropriate"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Claim
    claim_res = client.post(f"/api/v1/community/admin/reports/{rep_id}/claim", headers=admin_headers)
    assert claim_res.status_code == 200
    data = claim_res.json()
    assert data["status"] == "reviewing"
    assert data["claimed_by"] is not None
    assert data["claimed_at"] is not None


def test_10_admin_dismiss_report():
    """10. Admin dismisses an invalid report with required notes."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("dism_author")
    reporter, rep_headers = create_user("dism_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 4, "title": "Fine Review", "content": "Valid genuine content without violation", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "other", "description": "I just dislike this user"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Dismiss without notes should fail (< 3 chars)
    fail_res = client.post(f"/api/v1/community/admin/reports/{rep_id}/dismiss", json={"notes": "no"}, headers=admin_headers)
    assert fail_res.status_code == 422 or fail_res.status_code == 400

    # Dismiss with proper notes
    dism_res = client.post(
        f"/api/v1/community/admin/reports/{rep_id}/dismiss",
        json={"notes": "Báo cáo không có căn cứ, nội dung hợp lệ"},
        headers=admin_headers,
    )
    assert dism_res.status_code == 200
    assert dism_res.json()["status"] == "dismissed"
    assert dism_res.json()["admin_notes"] == "Báo cáo không có căn cứ, nội dung hợp lệ"


def test_11_admin_hide_review():
    """11. Admin hides an infringing review and verifies it disappears from public listings."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("hide_author")
    reporter, rep_headers = create_user("hide_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_002/reviews",
        json={"rating": 1, "title": "Scam website link", "content": "Click http://badlink.example.com to win", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "spam"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Admin takes action: hide
    act_res = client.post(
        f"/api/v1/community/admin/reports/{rep_id}/actions",
        json={"action": "hide", "reason": "Chứa liên kết lừa đảo độc hại"},
        headers=admin_headers,
    )
    assert act_res.status_code == 200
    assert act_res.json()["success"] is True

    # Public check: book reviews listing must NOT contain this review
    pub_res = client.get("/api/v1/community/books/book_002/reviews")
    assert pub_res.status_code == 200
    assert not any(r["id"] == rev_id for r in pub_res.json()["reviews"])

    # Detail check: ordinary user gets 404
    det_pub = client.get(f"/api/v1/community/reviews/{rev_id}", headers=rep_headers)
    assert det_pub.status_code == 404

    # Admin can still view in admin report detail
    admin_det = client.get(f"/api/v1/community/admin/reports/{rep_id}", headers=admin_headers)
    assert admin_det.status_code == 200
    assert admin_det.json()["target_status"] == "hidden"


def test_12_admin_hide_comment():
    """12. Admin hides an infringing comment and verifies it disappears from comments list."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("c_rev_author")
    commenter, comm_headers = create_user("c_bad_user")
    reporter, rep_headers = create_user("c_rep_user")

    rev_res = client.post(
        "/api/v1/community/books/book_003/reviews",
        json={"rating": 5, "title": "Good book", "content": "Pleasant reading experience", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    comm_res = client.post(
        f"/api/v1/community/reviews/{rev_id}/comments",
        json={"content": "Profane insults here"},
        headers=comm_headers,
    )
    comm_id = comm_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "comment", "target_id": comm_id, "reason": "harassment"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Admin hides comment
    act_res = client.post(
        f"/api/v1/community/admin/reports/{rep_id}/actions",
        json={"action": "hide", "reason": "Xúc phạm thành viên khác"},
        headers=admin_headers,
    )
    assert act_res.status_code == 200

    # Public comments list should not contain this comment
    c_list = client.get(f"/api/v1/community/reviews/{rev_id}/comments")
    assert c_list.status_code == 200
    assert not any(c["id"] == comm_id for c in c_list.json()["comments"])


def test_13_admin_delete_content():
    """13. Admin soft-deletes content and verifies status is deleted."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("del_author")
    reporter, rep_headers = create_user("del_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_004/reviews",
        json={"rating": 1, "title": "Severe violation", "content": "Extremely harmful content to be deleted", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "copyright"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Admin deletes
    act_res = client.post(
        f"/api/v1/community/admin/reports/{rep_id}/actions",
        json={"action": "delete", "reason": "Vi phạm nghiêm trọng bản quyền"},
        headers=admin_headers,
    )
    assert act_res.status_code == 200
    assert act_res.json()["action"]["new_status"] == "deleted"


def test_14_moderation_action_log_recorded():
    """14. Verify moderation action is recorded in moderation_actions audit table."""
    admin_headers = get_admin_headers()
    log_res = client.get("/api/v1/community/admin/moderation-actions?page=1&page_size=10", headers=admin_headers)
    assert log_res.status_code == 200
    data = log_res.json()
    assert data["total"] >= 1
    assert any(item["action"] in {"warn", "hide", "restore", "delete", "dismiss"} for item in data["items"])


def test_15_reporter_identity_privacy():
    """15. Regular users cannot see reporter identity via public APIs."""
    reporter, rep_headers = create_user("priv_reporter")
    other_user, other_headers = create_user("other_eavesdropper")
    author, auth_headers = create_user("priv_author")

    rev_res = client.post(
        "/api/v1/community/books/book_005/reviews",
        json={"rating": 2, "title": "Review to report", "content": "Review to test privacy leakage", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post(
        "/api/v1/community/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "other", "description": "Secret complaint"},
        headers=rep_headers,
    )
    rep_id = rep_res.json()["id"]

    # Other user checks their own reports list: should NOT contain reporter's report
    my_rep = client.get("/api/v1/community/me/reports", headers=other_headers)
    assert not any(r["id"] == rep_id for r in my_rep.json()["items"])

    # Other user cannot call admin endpoint to view reporter info
    forbidden_res = client.get(f"/api/v1/community/admin/reports/{rep_id}", headers=other_headers)
    assert forbidden_res.status_code == 403


def test_16_moderation_log_immutable():
    """16. Moderation action log cannot be modified or deleted via public API."""
    user, user_headers = create_user("hacker_user")

    # DELETE /admin/moderation-actions -> Not allowed or 403/405
    res1 = client.delete("/api/v1/community/admin/moderation-actions", headers=user_headers)
    assert res1.status_code in {403, 404, 405}

    # PUT /admin/moderation-actions -> Not allowed or 403/405
    res2 = client.put("/api/v1/community/admin/moderation-actions", headers=user_headers)
    assert res2.status_code in {403, 404, 405}


def test_17_activity_feed_hides_moderated_reviews():
    """17. Activity Feed automatically conceals reviews that have been hidden or deleted."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("feed_author_mod")
    follower, fol_headers = create_user("feed_follower_mod")

    # Follower follows author
    client.post(f"/api/v1/community/users/{author}/follow", headers=fol_headers)

    # Author creates a review
    rev_res = client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 1, "title": "Toxic Review in Feed", "content": "Toxic content to be hidden by admin", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    # Activity visible in feed initially
    f1 = client.get("/api/v1/community/feed", headers=fol_headers).json()
    assert any(it["entity_id"] == rev_id for it in f1["items"])

    # Reporter reports it
    reporter, rep_headers = create_user("rep_feed")
    rep_res = client.post("/api/v1/community/reports", json={"target_type": "review", "target_id": rev_id, "reason": "harassment"}, headers=rep_headers)
    rep_id = rep_res.json()["id"]

    # Admin hides the review
    client.post(f"/api/v1/community/admin/reports/{rep_id}/actions", json={"action": "hide", "reason": "Toxic language"}, headers=admin_headers)

    # Activity must be immediately hidden from feed
    f2 = client.get("/api/v1/community/feed", headers=fol_headers).json()
    assert not any(it["entity_id"] == rev_id for it in f2["items"])


def test_18_concurrent_admin_claim_and_action():
    """18. Race condition test: Two Admins concurrently claiming the same report."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("race_author")
    reporter, rep_headers = create_user("race_reporter")

    rev_res = client.post(
        "/api/v1/community/books/book_002/reviews",
        json={"rating": 2, "title": "Race Test Title", "content": "Content to test race condition", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    rep_res = client.post("/api/v1/community/reports", json={"target_type": "review", "target_id": rev_id, "reason": "spam"}, headers=rep_headers)
    rep_id = rep_res.json()["id"]

    def claim_report():
        return client.post(f"/api/v1/community/admin/reports/{rep_id}/claim", headers=admin_headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(claim_report) for _ in range(2)]
        results = [f.result() for f in futures]

    # Both or at least one must successfully transition to reviewing without 500 error
    assert any(r.status_code == 200 for r in results)
    for r in results:
        assert r.status_code in {200, 409}


def test_19_multiple_reports_same_target_resolved_together():
    """19. When admin hides/deletes content, all other pending reports on the same target are resolved."""
    admin_headers = get_admin_headers()
    author, auth_headers = create_user("multi_author")
    rep1, h1 = create_user("multi_rep1")
    rep2, h2 = create_user("multi_rep2")

    rev_res = client.post(
        "/api/v1/community/books/book_003/reviews",
        json={"rating": 1, "title": "Mass reported review", "content": "Massive spam review with multiple complaints", "contains_spoiler": False},
        headers=auth_headers,
    )
    rev_id = rev_res.json()["id"]

    # Rep1 reports
    r1 = client.post("/api/v1/community/reports", json={"target_type": "review", "target_id": rev_id, "reason": "spam"}, headers=h1)
    rep1_id = r1.json()["id"]

    # Rep2 reports
    r2 = client.post("/api/v1/community/reports", json={"target_type": "review", "target_id": rev_id, "reason": "inappropriate"}, headers=h2)
    rep2_id = r2.json()["id"]

    # Admin takes action on rep1_id: hide
    act_res = client.post(
        f"/api/v1/community/admin/reports/{rep1_id}/actions",
        json={"action": "hide", "reason": "Xử lý hàng loạt nội dung spam"},
        headers=admin_headers,
    )
    assert act_res.status_code == 200

    # Both reports must now be 'resolved'
    d1 = client.get(f"/api/v1/community/admin/reports/{rep1_id}", headers=admin_headers).json()
    d2 = client.get(f"/api/v1/community/admin/reports/{rep2_id}", headers=admin_headers).json()
    assert d1["status"] == "resolved"
    assert d2["status"] == "resolved"


def test_20_migration_v3_schema_and_idempotency_on_isolated_db(tmp_path):
    """20. Verify Migration v3 idempotency, schema tables, and foreign keys on isolated database."""
    test_db = tmp_path / "test_mod_migration.db"
    
    # Run migrations 1, 2, 3
    v = run_migrations(test_db)
    assert v == 3

    # Re-run: must be idempotent and remain at version 3
    v_rerun = run_migrations(test_db)
    assert v_rerun == 3

    conn = create_connection(test_db)
    try:
        # Check foreign keys
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1

        # Check tables existence
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {r["name"] for r in cur.fetchall()}
        assert "reports" in tables
        assert "moderation_actions" in tables
        assert "schema_migrations" in tables
    finally:
        conn.close()

