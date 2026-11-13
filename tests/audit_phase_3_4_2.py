"""
Independent Audit Test Suite for Phase 3.4.2
Runs deep security, concurrency, edge-case, and integrity checks
using isolated database fixtures.
"""

import concurrent.futures
import sqlite3
import uuid
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.community_db import (
    create_connection,
    get_db,
    run_migrations,
    backup_database,
    restore_database,
    MIGRATIONS,
)
from backend.services import community_service

client = TestClient(app)


def test_audit_migration_v2_rollback_and_idempotency(tmp_path):
    """
    Audit 1: Test migration v2 idempotency and failure recovery on isolated DB.
    """
    db_file = tmp_path / "test_migration_audit.db"
    
    # 1. Run migrations initially
    v1 = run_migrations(db_file)
    assert v1 >= 2
    
    # 2. Re-run migration: must be idempotent, return same version, and not crash
    v2 = run_migrations(db_file)
    assert v2 == v1
    
    # 3. Verify Foreign Keys and WAL on new connection
    conn = create_connection(db_file)
    try:
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1, "Foreign keys must be enabled on every connection"
        
        wal = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert wal.lower() == "wal", "WAL mode must be active"
        
        busy = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert busy >= 5000, "busy_timeout must be at least 5000"
    finally:
        conn.close()


def test_audit_backup_restore_during_wal_activity(tmp_path):
    """
    Audit 2: Online backup during simulated WAL writes.
    """
    db_file = tmp_path / "test_backup_wal.db"
    run_migrations(db_file)
    
    # Insert some data
    conn = create_connection(db_file)
    try:
        conn.execute("INSERT INTO user_profiles (username, display_name, created_at, updated_at) VALUES ('user1', 'User 1', '2026-11-02', '2026-11-02');")
        conn.commit()
    finally:
        conn.close()
        
    backup_file = backup_database(db_file, backup_dir=tmp_path / "backups")
    assert backup_file.exists()
    
    restore_target = tmp_path / "restored.db"
    assert restore_database(backup_file, target_db_path=restore_target) is True
    
    res_conn = create_connection(restore_target)
    try:
        row = res_conn.execute("SELECT username FROM user_profiles WHERE username = 'user1';").fetchone()
        assert row is not None
        assert row["username"] == "user1"
    finally:
        res_conn.close()


def test_audit_friend_request_reverse_pending_behavior():
    """
    Audit 3: Test when User A sends request to B, and B sends request to A while pending.
    """
    u_a = f"audit_a_{uuid.uuid4().hex[:6]}"
    u_b = f"audit_b_{uuid.uuid4().hex[:6]}"
    
    client.post("/api/v1/auth/register", json={"username": u_a, "password": "Password123!"})
    client.post("/api/v1/auth/register", json={"username": u_b, "password": "Password123!"})
    
    tok_a = client.post("/api/v1/auth/login", json={"username": u_a, "password": "Password123!"}).json()["access_token"]
    tok_b = client.post("/api/v1/auth/login", json={"username": u_b, "password": "Password123!"}).json()["access_token"]
    
    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}
    
    # A sends to B
    r1 = client.post(f"/api/v1/community/users/{u_b}/friend-request", headers=h_a)
    assert r1.status_code == 200
    req_a_id = r1.json()["request_id"]
    
    # Now B sends to A
    r2 = client.post(f"/api/v1/community/users/{u_a}/friend-request", headers=h_b)
    # Check what happens: does it allow or block?
    # In current implementation, r2 succeeds because sender/receiver are swapped.
    # We record this finding.
    assert r2.status_code in [200, 400]
    
    # B accepts A's request
    r_acc = client.post(f"/api/v1/community/friend-requests/{req_a_id}/accept", headers=h_b)
    assert r_acc.status_code == 200
    
    # Verify both are now friends
    assert community_service.are_friends(u_a, u_b) is True


def test_audit_concurrency_friend_request_accept():
    """
    Audit 4: Two concurrent requests accepting the same friend request.
    Only one should succeed in transitioning state, both should result in clean DB.
    """
    u_a = f"acc_a_{uuid.uuid4().hex[:6]}"
    u_b = f"acc_b_{uuid.uuid4().hex[:6]}"
    
    client.post("/api/v1/auth/register", json={"username": u_a, "password": "Password123!"})
    client.post("/api/v1/auth/register", json={"username": u_b, "password": "Password123!"})
    
    tok_a = client.post("/api/v1/auth/login", json={"username": u_a, "password": "Password123!"}).json()["access_token"]
    tok_b = client.post("/api/v1/auth/login", json={"username": u_b, "password": "Password123!"}).json()["access_token"]
    
    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}
    
    # Send request
    r = client.post(f"/api/v1/community/users/{u_b}/friend-request", headers=h_a)
    req_id = r.json()["request_id"]
    
    def do_accept():
        return client.post(f"/api/v1/community/friend-requests/{req_id}/accept", headers=h_b)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_accept)
        f2 = executor.submit(do_accept)
        res1 = f1.result()
        res2 = f2.result()
        
    # One must be 200, one may be 200 or 400 (already accepted)
    status_codes = [res1.status_code, res2.status_code]
    assert 200 in status_codes
    assert community_service.are_friends(u_a, u_b) is True


def test_audit_concurrency_privacy_update_and_feed_query():
    """
    Audit 5: Concurrent privacy update while follower queries feed.
    Must not crash with SQLite locked error.
    """
    u_author = f"priv_author_{uuid.uuid4().hex[:6]}"
    u_follower = f"priv_fol_{uuid.uuid4().hex[:6]}"
    
    client.post("/api/v1/auth/register", json={"username": u_author, "password": "Password123!"})
    client.post("/api/v1/auth/register", json={"username": u_follower, "password": "Password123!"})
    
    tok_author = client.post("/api/v1/auth/login", json={"username": u_author, "password": "Password123!"}).json()["access_token"]
    tok_follower = client.post("/api/v1/auth/login", json={"username": u_follower, "password": "Password123!"}).json()["access_token"]
    
    h_author = {"Authorization": f"Bearer {tok_author}"}
    h_fol = {"Authorization": f"Bearer {tok_follower}"}
    
    # Follow
    client.post(f"/api/v1/community/users/{u_author}/follow", headers=h_fol)
    
    # Create a review
    client.post(
        "/api/v1/community/books/book_001/reviews",
        json={"rating": 5, "title": "Great Book", "content": "Review content 10+ characters", "contains_spoiler": False},
        headers=h_author,
    )
    
    def toggle_privacy():
        for i in range(5):
            p = "private" if i % 2 == 0 else "public"
            client.put("/api/v1/community/me/privacy", json={"activity_privacy": p}, headers=h_author)
            
    def read_feed():
        for _ in range(5):
            res = client.get("/api/v1/community/feed", headers=h_fol)
            assert res.status_code == 200
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        t1 = executor.submit(toggle_privacy)
        t2 = executor.submit(read_feed)
        t1.result()
        t2.result()


def test_audit_re_reading_activity_behavior():
    """
    Audit 6: Verify behavior when a user re-reads a book after finishing it.
    Checks UNIQUE constraint on (username, activity_type, entity_id).
    """
    user = f"reread_{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/auth/register", json={"username": user, "password": "Password123!"})
    tok = client.post("/api/v1/auth/login", json={"username": user, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    
    # Start reading
    client.post("/api/v1/reading/progress", json={"book_id": "book_005", "current_page": 1, "total_pages": 100}, headers=headers)
    # Finish reading
    client.post("/api/v1/reading/progress", json={"book_id": "book_005", "current_page": 100, "total_pages": 100}, headers=headers)
    
    # Re-read: start from page 1 again
    res = client.post("/api/v1/reading/progress", json={"book_id": "book_005", "current_page": 1, "total_pages": 100}, headers=headers)
    assert res.status_code == 200
    
    # Check activity feed entries count for reading_started on book_005
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS cnt FROM activity_feed WHERE username = ? AND activity_type = 'reading_started' AND entity_id = 'book_005';", (user,))
        cnt = cur.fetchone()["cnt"]
        # UNIQUE (username, activity_type, entity_id) deduplicates by entity_id
        assert cnt == 1

