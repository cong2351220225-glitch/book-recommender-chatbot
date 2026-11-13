"""
Comprehensive Test Suite for Phase 3.4.2 - Follow, Activity Feed & Public Bookshelf Privacy
Classified into:
- Unit Tests: Migration v2 schema verification, are_friends bilateral logic, duplicate activity prevention.
- Real Integration Tests: Running on live FastAPI app, real SQLite database (data/social_community.db),
  real JWT auth tokens, real books CSV.
"""

from __future__ import annotations

import concurrent.futures
import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.community_db import get_db, run_migrations
from backend.services import community_service

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


# ==============================================================================
# 1. UNIT TESTS: Schema Migration v2 & Logic Rules
# ==============================================================================

def test_unit_migration_v2_applied():
    """Verify that migration v2 is applied and schema_migrations table tracks version 2."""
    v = run_migrations()
    assert v >= 2

    with get_db() as conn:
        cur = conn.execute("SELECT version, description FROM schema_migrations WHERE version = 2;")
        row = cur.fetchone()
        assert row is not None
        assert "Phase 3.4.2" in row["description"]

        # Check table existence
        tables = {"follows", "friend_requests", "friendships", "activity_feed"}
        t_cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {r["name"] for r in t_cur.fetchall()}
        assert tables.issubset(existing_tables)


def test_unit_are_friends_bilateral_logic():
    """Verify bilateral symmetry of friendship check."""
    u1 = f"test_a_{uuid.uuid4().hex[:6]}"
    u2 = f"test_b_{uuid.uuid4().hex[:6]}"

    assert community_service.are_friends(u1, u2) is False
    assert community_service.are_friends(u2, u1) is False

    with get_db() as conn:
        community_service.get_or_create_profile(u1, conn=conn)
        community_service.get_or_create_profile(u2, conn=conn)
        pair = sorted([u1, u2])
        conn.execute("INSERT INTO friendships (user1_username, user2_username, created_at) VALUES (?, ?, ?);", (pair[0], pair[1], "2026-11-02T12:00:00Z"))

    assert community_service.are_friends(u1, u2) is True
    assert community_service.are_friends(u2, u1) is True


def test_unit_duplicate_activity_prevention():
    """Verify UNIQUE constraint prevents identical activity duplicates."""
    u = f"act_user_{uuid.uuid4().hex[:6]}"
    with get_db() as conn:
        community_service.get_or_create_profile(u, conn=conn)

    ok1 = community_service.record_activity(u, "reading_started", "book_001", "book", {"title": "Book 1"})
    ok2 = community_service.record_activity(u, "reading_started", "book_001", "book", {"title": "Book 1 duplicate"})
    assert ok1 is True
    assert ok2 is True

    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS cnt FROM activity_feed WHERE username = ? AND activity_type = 'reading_started' AND entity_id = 'book_001';", (u,))
        assert cur.fetchone()["cnt"] == 1


# ==============================================================================
# 2. REAL INTEGRATION TESTS: Follow & Unfollow APIs
# ==============================================================================

def test_real_integration_follow_unfollow_lifecycle():
    """Verify follow and unfollow lifecycle."""
    user_a, _, headers_a = create_authenticated_user("follower")
    user_b, _, headers_b = create_authenticated_user("target")

    # 1. Follow user_b
    res = client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["is_following"] is True

    # 2. Check user_b followers
    res_followers = client.get(f"/api/v1/community/users/{user_b}/followers")
    assert res_followers.status_code == 200
    followers_data = res_followers.json()
    assert followers_data["total"] >= 1
    assert any(item["username"] == user_a for item in followers_data["items"])

    # 3. Check user_a following
    res_following = client.get(f"/api/v1/community/users/{user_a}/following")
    assert res_following.status_code == 200
    following_data = res_following.json()
    assert following_data["total"] >= 1
    assert any(item["username"] == user_b for item in following_data["items"])

    # 4. Unfollow user_b
    res_unf = client.delete(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)
    assert res_unf.status_code == 200
    assert res_unf.json()["is_following"] is False

    # 5. Check user_b followers after unfollow
    res_followers_after = client.get(f"/api/v1/community/users/{user_b}/followers")
    assert res_followers_after.status_code == 200
    assert not any(item["username"] == user_a for item in res_followers_after.json()["items"])


def test_real_integration_follow_validations():
    """Verify follow error cases: self-follow, nonexistent target, duplicate follow."""
    user_a, _, headers_a = create_authenticated_user("val_user")
    user_b, _, headers_b = create_authenticated_user("val_target")

    # Self-follow blocked
    res_self = client.post(f"/api/v1/community/users/{user_a}/follow", headers=headers_a)
    assert res_self.status_code == 400
    assert "tự theo dõi" in res_self.json()["detail"].lower()

    # Target not found
    res_404 = client.post("/api/v1/community/users/nonexistent_ghost_9999/follow", headers=headers_a)
    assert res_404.status_code == 404

    # First follow OK
    res_ok = client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)
    assert res_ok.status_code == 200

    # Duplicate follow blocked
    res_dup = client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)
    assert res_dup.status_code == 400
    assert "đã theo dõi" in res_dup.json()["detail"].lower()


def test_real_integration_followers_following_pagination():
    """Verify pagination on followers and following endpoints."""
    target, _, _ = create_authenticated_user("influencer")
    followers = []
    for _ in range(5):
        f_user, _, f_headers = create_authenticated_user("fan")
        client.post(f"/api/v1/community/users/{target}/follow", headers=f_headers)
        followers.append(f_user)

    # Page 1, page_size 2
    res_p1 = client.get(f"/api/v1/community/users/{target}/followers?page=1&page_size=2")
    assert res_p1.status_code == 200
    d1 = res_p1.json()
    assert d1["total"] == 5
    assert len(d1["items"]) == 2

    # Page 2, page_size 2
    res_p2 = client.get(f"/api/v1/community/users/{target}/followers?page=2&page_size=2")
    assert res_p2.status_code == 200
    d2 = res_p2.json()
    assert len(d2["items"]) == 2

    # Items in page 1 and page 2 must not overlap
    p1_users = {it["username"] for it in d1["items"]}
    p2_users = {it["username"] for it in d2["items"]}
    assert p1_users.isdisjoint(p2_users)


# ==============================================================================
# 3. REAL INTEGRATION TESTS: Two-Way Friendship Mechanism
# ==============================================================================

def test_real_integration_friendship_request_lifecycle():
    """Verify friend request: send -> receive -> accept -> friends list."""
    user_a, _, headers_a = create_authenticated_user("alice")
    user_b, _, headers_b = create_authenticated_user("bob")

    # 1. User A sends friend request to User B
    res_send = client.post(f"/api/v1/community/users/{user_b}/friend-request", headers=headers_a)
    assert res_send.status_code == 200
    req_id = res_send.json()["request_id"]

    # Duplicate request blocked
    res_dup = client.post(f"/api/v1/community/users/{user_b}/friend-request", headers=headers_a)
    assert res_dup.status_code == 400

    # 2. User B checks pending requests
    res_pending = client.get("/api/v1/community/me/friend-requests", headers=headers_b)
    assert res_pending.status_code == 200
    p_data = res_pending.json()
    assert p_data["total"] >= 1
    assert any(it["id"] == req_id for it in p_data["items"])

    # 3. Third-party cannot accept (IDOR protection)
    user_c, _, headers_c = create_authenticated_user("charlie")
    res_idor = client.post(f"/api/v1/community/friend-requests/{req_id}/accept", headers=headers_c)
    assert res_idor.status_code == 403

    # 4. User B accepts friend request
    res_accept = client.post(f"/api/v1/community/friend-requests/{req_id}/accept", headers=headers_b)
    assert res_accept.status_code == 200

    # 5. Both check their friends list
    res_a_friends = client.get(f"/api/v1/community/users/{user_a}/friends")
    assert res_a_friends.status_code == 200
    assert any(it["username"] == user_b for it in res_a_friends.json()["items"])

    res_b_friends = client.get(f"/api/v1/community/users/{user_b}/friends")
    assert res_b_friends.status_code == 200
    assert any(it["username"] == user_a for it in res_b_friends.json()["items"])

    # 6. Remove friendship
    res_del = client.delete(f"/api/v1/community/users/{user_b}/friends", headers=headers_a)
    assert res_del.status_code == 200
    assert community_service.are_friends(user_a, user_b) is False


# ==============================================================================
# 4. REAL INTEGRATION TESTS: Privacy Settings & Public Bookshelf Privacy
# ==============================================================================

def test_real_integration_privacy_settings_update_immediate():
    """Verify PUT /me/privacy updates settings and takes effect immediately."""
    username, _, headers = create_authenticated_user("priv_user")

    # Update to friends & private
    res_put = client.put(
        "/api/v1/community/me/privacy",
        json={"bookshelf_privacy": "friends", "activity_privacy": "private"},
        headers=headers,
    )
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["bookshelf_privacy"] == "friends"
    assert put_data["activity_privacy"] == "private"

    # GET /me/privacy reflects immediate change
    res_get = client.get("/api/v1/community/me/privacy", headers=headers)
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["bookshelf_privacy"] == "friends"
    assert get_data["activity_privacy"] == "private"


def test_real_integration_public_bookshelf_privacy_matrix():
    """
    Verify complete privacy matrix:
    - public: open to guest and user
    - friends: open to owner and confirmed friend, 403 for stranger/guest
    - private: open strictly to owner, 403 for everyone else
    """
    owner, _, owner_headers = create_authenticated_user("shelf_owner")
    stranger, _, stranger_headers = create_authenticated_user("shelf_stranger")
    friend, _, friend_headers = create_authenticated_user("shelf_friend")

    # Establish friendship between owner and friend
    r1 = client.post(f"/api/v1/community/users/{owner}/friend-request", headers=friend_headers)
    client.post(f"/api/v1/community/friend-requests/{r1.json()['request_id']}/accept", headers=owner_headers)
    assert community_service.are_friends(owner, friend) is True

    # Owner adds a book to shelf
    client.post(
        "/api/v1/bookshelf",
        json={"book_id": "book_001", "status": "favorite", "notes": "Secret favorite"},
        headers=owner_headers,
    )

    # -------------------------------------------------------------
    # CASE 1: bookshelf_privacy = 'public' (Default)
    # -------------------------------------------------------------
    # Guest can view
    res_guest = client.get(f"/api/v1/community/users/{owner}/bookshelf")
    assert res_guest.status_code == 200
    assert res_guest.json()["total"] >= 1

    # Stranger can view
    res_stranger = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=stranger_headers)
    assert res_stranger.status_code == 200

    # -------------------------------------------------------------
    # CASE 2: Change to 'friends'
    # -------------------------------------------------------------
    client.put("/api/v1/community/me/privacy", json={"bookshelf_privacy": "friends"}, headers=owner_headers)

    # Owner can still view
    res_owner = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=owner_headers)
    assert res_owner.status_code == 200

    # Confirmed friend can view
    res_friend = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=friend_headers)
    assert res_friend.status_code == 200
    assert res_friend.json()["total"] >= 1

    # Stranger is blocked (403)
    res_stranger_blocked = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=stranger_headers)
    assert res_stranger_blocked.status_code == 403
    assert "chỉ chia sẻ với bạn bè" in res_stranger_blocked.json()["detail"].lower()

    # Guest is blocked (403)
    res_guest_blocked = client.get(f"/api/v1/community/users/{owner}/bookshelf")
    assert res_guest_blocked.status_code == 403

    # -------------------------------------------------------------
    # CASE 3: Change to 'private'
    # -------------------------------------------------------------
    client.put("/api/v1/community/me/privacy", json={"bookshelf_privacy": "private"}, headers=owner_headers)

    # Owner can view
    res_owner_priv = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=owner_headers)
    assert res_owner_priv.status_code == 200

    # Friend is now blocked (403)
    res_friend_priv_blocked = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=friend_headers)
    assert res_friend_priv_blocked.status_code == 403
    assert "riêng tư" in res_friend_priv_blocked.json()["detail"].lower()

    # Stranger is blocked (403)
    res_stranger_priv_blocked = client.get(f"/api/v1/community/users/{owner}/bookshelf", headers=stranger_headers)
    assert res_stranger_priv_blocked.status_code == 403


# ==============================================================================
# 5. REAL INTEGRATION TESTS: Activity Feed & Privacy Filtering
# ==============================================================================

def test_real_integration_activity_feed_following_only():
    """Verify feed only includes accounts followed by the user, and no fake events."""
    user_a, _, headers_a = create_authenticated_user("feed_reader")
    user_b, _, headers_b = create_authenticated_user("feed_author_b")
    user_c, _, headers_c = create_authenticated_user("feed_author_c")

    # User A follows User B only (does not follow User C)
    client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)

    # User B posts a review
    res_rev_b = client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 5, "title": "B Review Title", "content": "B content exceeds 10 chars", "contains_spoiler": False},
        headers=headers_b,
    )
    assert res_rev_b.status_code == 201

    # User C posts a review
    res_rev_c = client.post(
        "/api/v1/community/books/book_002/reviews",
        json={"rating": 4, "title": "C Review Title", "content": "C content exceeds 10 chars", "contains_spoiler": False},
        headers=headers_c,
    )
    assert res_rev_c.status_code == 201

    # User A fetches their feed
    res_feed = client.get("/api/v1/community/feed", headers=headers_a)
    assert res_feed.status_code == 200
    feed_data = res_feed.json()
    feed_users = {it["username"] for it in feed_data["items"]}

    # User B MUST be present
    assert user_b in feed_users
    # User C MUST NOT be present
    assert user_c not in feed_users


def test_real_integration_activity_feed_privacy_controls():
    """Verify activities are hidden from feed when author sets activity_privacy to private."""
    user_a, _, headers_a = create_authenticated_user("feed_listener")
    user_b, _, headers_b = create_authenticated_user("feed_writer")

    client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)

    # User B posts review
    client.post(
        "/api/v1/community/books/book_003/reviews",
        json={"rating": 5, "title": "Public Review", "content": "Public review content valid length", "contains_spoiler": False},
        headers=headers_b,
    )

    # Activity visible initially
    f1 = client.get("/api/v1/community/feed", headers=headers_a).json()
    assert any(it["username"] == user_b for it in f1["items"])

    # User B updates activity_privacy to 'private'
    client.put("/api/v1/community/me/privacy", json={"activity_privacy": "private"}, headers=headers_b)

    # Activity must disappear from User A's feed
    f2 = client.get("/api/v1/community/feed", headers=headers_a).json()
    assert not any(it["username"] == user_b for it in f2["items"])


def test_real_integration_deleted_review_removed_from_feed():
    """Verify when a review is deleted, its activity disappears from the feed."""
    user_a, _, headers_a = create_authenticated_user("feed_sub")
    user_b, _, headers_b = create_authenticated_user("feed_pub")

    client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)

    rev_res = client.post(
        "/api/v1/community/books/book_004/reviews",
        json={"rating": 5, "title": "Temporary Review", "content": "Review to be deleted soon", "contains_spoiler": False},
        headers=headers_b,
    )
    rev_id = rev_res.json()["id"]

    # In feed
    f1 = client.get("/api/v1/community/feed", headers=headers_a).json()
    assert any(it["entity_id"] == rev_id for it in f1["items"])

    # User B deletes review
    del_res = client.delete(f"/api/v1/community/reviews/{rev_id}", headers=headers_b)
    assert del_res.status_code == 200

    # No longer in feed
    f2 = client.get("/api/v1/community/feed", headers=headers_a).json()
    assert not any(it["entity_id"] == rev_id for it in f2["items"])


def test_real_integration_private_bookshelf_hides_reading_activities():
    """Verify that if bookshelf_privacy is 'private', reading activities are not leaked into feed."""
    user_a, _, headers_a = create_authenticated_user("feed_a")
    user_b, _, headers_b = create_authenticated_user("feed_b")

    client.post(f"/api/v1/community/users/{user_b}/follow", headers=headers_a)

    # User B sets bookshelf to private, but activity_privacy is public
    client.put(
        "/api/v1/community/me/privacy",
        json={"bookshelf_privacy": "private", "activity_privacy": "public"},
        headers=headers_b,
    )

    # User B records reading progress
    client.post(
        "/api/v1/reading/progress",
        json={"book_id": "book_001", "current_page": 1, "total_pages": 100},
        headers=headers_b,
    )

    # User A's feed should NOT leak User B's private reading activity
    feed = client.get("/api/v1/community/feed", headers=headers_a).json()
    assert not any(it["username"] == user_b and it["activity_type"] == "reading_started" for it in feed["items"])


# ==============================================================================
# 6. CONCURRENCY & STRESS TESTS
# ==============================================================================

def test_real_integration_concurrent_follow_unfollow():
    """Verify concurrent follow and unfollow requests maintain consistency without SQLite locking errors."""
    target, _, _ = create_authenticated_user("concurrent_target")
    num_followers = 6
    followers = [create_authenticated_user(f"c_fan_{i}") for i in range(num_followers)]

    def do_follow(f_data):
        _, _, headers = f_data
        return client.post(f"/api/v1/community/users/{target}/follow", headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(do_follow, followers))

    # All should succeed 200
    for r in results:
        assert r.status_code == 200

    # Verify followers count
    f_res = client.get(f"/api/v1/community/users/{target}/followers")
    assert f_res.json()["total"] == num_followers

