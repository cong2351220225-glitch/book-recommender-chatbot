"""
Social Community Database Module (SQLite WAL Engine)
Provides thread-safe connections, automated versioned migrations,
ACID transactions, and online backup/restore utilities.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from backend.core.config import COMMUNITY_DB_PATH

LOGGER = logging.getLogger(__name__)

# Migration scripts registry
MIGRATIONS = [
    (
        1,
        "Initial social community schema: user_profiles, reviews, comments, reactions",
        """
        -- 1. User Profiles
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            avatar_url TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- 2. Book Reviews
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            book_id TEXT NOT NULL,
            username TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            contains_spoiler INTEGER NOT NULL DEFAULT 0,
            likes_count INTEGER NOT NULL DEFAULT 0,
            comments_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'hidden', 'deleted')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE RESTRICT,
            UNIQUE (book_id, username)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_book_id ON reviews(book_id, status);
        CREATE INDEX IF NOT EXISTS idx_reviews_username ON reviews(username);
        CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);

        -- 3. Threaded Comments
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            review_id TEXT NOT NULL,
            username TEXT NOT NULL,
            parent_comment_id TEXT NULL,
            content TEXT NOT NULL,
            likes_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'hidden', 'deleted')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_comment_id) REFERENCES comments(id) ON DELETE CASCADE,
            FOREIGN KEY (username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_comments_review_id ON comments(review_id, status);
        CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_comment_id);
        CREATE INDEX IF NOT EXISTS idx_comments_username ON comments(username);

        -- 4. Reactions / Likes
        CREATE TABLE IF NOT EXISTS reactions (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            target_type TEXT NOT NULL CHECK (target_type IN ('review', 'comment')),
            target_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE (username, target_type, target_id)
        );

        CREATE INDEX IF NOT EXISTS idx_reactions_target ON reactions(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_reactions_user ON reactions(username);
        """,
    ),
    (
        2,
        "Phase 3.4.2: follows, friend_requests, friendships, activity_feed, and privacy settings in user_profiles",
        """
        -- 1. Extend user_profiles with privacy settings
        ALTER TABLE user_profiles ADD COLUMN bookshelf_privacy TEXT NOT NULL DEFAULT 'public';
        ALTER TABLE user_profiles ADD COLUMN activity_privacy TEXT NOT NULL DEFAULT 'public';

        -- 2. Follows table (one-way relationship)
        CREATE TABLE IF NOT EXISTS follows (
            follower_username TEXT NOT NULL,
            following_username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (follower_username, following_username),
            FOREIGN KEY (follower_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (following_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            CHECK (follower_username != following_username)
        );

        CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_username);
        CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_username);

        -- 3. Friend requests table
        CREATE TABLE IF NOT EXISTS friend_requests (
            id TEXT PRIMARY KEY,
            sender_username TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (sender_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (receiver_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            CHECK (sender_username != receiver_username),
            UNIQUE (sender_username, receiver_username)
        );

        CREATE INDEX IF NOT EXISTS idx_friend_requests_receiver ON friend_requests(receiver_username, status);
        CREATE INDEX IF NOT EXISTS idx_friend_requests_sender ON friend_requests(sender_username, status);

        -- 4. Friendships table (bidirectional friendship mechanism)
        CREATE TABLE IF NOT EXISTS friendships (
            user1_username TEXT NOT NULL,
            user2_username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user1_username, user2_username),
            FOREIGN KEY (user1_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (user2_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            CHECK (user1_username < user2_username)
        );

        CREATE INDEX IF NOT EXISTS idx_friendships_user1 ON friendships(user1_username);
        CREATE INDEX IF NOT EXISTS idx_friendships_user2 ON friendships(user2_username);

        -- 5. Activity Feed
        CREATE TABLE IF NOT EXISTS activity_feed (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            activity_type TEXT NOT NULL CHECK (activity_type IN ('review_created', 'reading_started', 'book_completed')),
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            is_hidden INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE (username, activity_type, entity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_activity_feed_user ON activity_feed(username, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_activity_feed_type ON activity_feed(activity_type);
        """,
    ),
    (
        3,
        "Phase 3.4.3: Social community moderation - reports and moderation_actions tables",
        """
        BEGIN TRANSACTION;

        -- 1. Reports table
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            reporter_username TEXT NOT NULL,
            target_type TEXT NOT NULL CHECK (target_type IN ('review', 'comment')),
            target_id TEXT NOT NULL,
            reason TEXT NOT NULL CHECK (reason IN ('spam', 'harassment', 'misinformation', 'inappropriate', 'copyright', 'other')),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewing', 'resolved', 'dismissed')),
            claimed_by TEXT NULL,
            claimed_at TEXT NULL,
            resolved_by TEXT NULL,
            resolved_at TEXT NULL,
            admin_notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (reporter_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_target ON reports(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter_username);
        CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);

        -- 2. Moderation actions log table
        CREATE TABLE IF NOT EXISTS moderation_actions (
            id TEXT PRIMARY KEY,
            admin_username TEXT NOT NULL,
            target_type TEXT NOT NULL CHECK (target_type IN ('review', 'comment')),
            target_id TEXT NOT NULL,
            report_id TEXT NULL,
            action TEXT NOT NULL CHECK (action IN ('warn', 'hide', 'restore', 'delete', 'dismiss')),
            previous_status TEXT NOT NULL DEFAULT '',
            new_status TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (admin_username) REFERENCES user_profiles(username) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mod_target ON moderation_actions(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_mod_admin ON moderation_actions(admin_username);
        CREATE INDEX IF NOT EXISTS idx_mod_created ON moderation_actions(created_at DESC);

        COMMIT;
        """,
    ),
]


def create_connection(db_path: Path = COMMUNITY_DB_PATH) -> sqlite3.Connection:
    """Create a configured SQLite connection with WAL mode and foreign keys enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        timeout=10.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db(db_path: Path = COMMUNITY_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing an ACID transactional SQLite connection."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        LOGGER.error("Database transaction rolled back due to error: %s", exc)
        raise
    finally:
        conn.close()


def run_migrations(db_path: Path = COMMUNITY_DB_PATH) -> int:
    """Run pending migrations safely. Returns the current applied schema version."""
    with get_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT NOT NULL
            );
            """
        )

        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
        applied_versions = {row["version"] for row in cursor.fetchall()}

        newly_applied = 0
        for version, description, script in MIGRATIONS:
            if version not in applied_versions:
                LOGGER.info("Applying migration v%d: %s", version, description)
                conn.executescript(script)
                now_iso = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?);",
                    (version, now_iso, description),
                )
                newly_applied += 1

        cursor = conn.execute("SELECT MAX(version) AS max_v FROM schema_migrations;")
        row = cursor.fetchone()
        latest_version = row["max_v"] if row and row["max_v"] is not None else 0
        LOGGER.info("Community database schema is at version %d (applied %d new)", latest_version, newly_applied)
        return latest_version


def backup_database(
    source_db_path: Path = COMMUNITY_DB_PATH,
    backup_dir: Path | None = None,
) -> Path:
    """
    Online non-blocking SQLite backup using the native sqlite3 backup API.
    Works safely while concurrent reads/writes are happening.
    """
    if backup_dir is None:
        backup_dir = source_db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"social_community_{timestamp}.db"

    source_conn = create_connection(source_db_path)
    target_conn = sqlite3.connect(str(backup_file))
    try:
        source_conn.backup(target_conn, pages=100)
        LOGGER.info("Community database backed up successfully to %s", backup_file)
    finally:
        target_conn.close()
        source_conn.close()

    return backup_file


def restore_database(
    backup_file: Path,
    target_db_path: Path = COMMUNITY_DB_PATH,
) -> bool:
    """
    Restore database from a verified backup file.
    """
    if not backup_file.exists():
        LOGGER.error("Backup file %s does not exist for restore", backup_file)
        return False

    backup_conn = sqlite3.connect(str(backup_file))
    target_conn = create_connection(target_db_path)
    try:
        backup_conn.backup(target_conn, pages=100)
        LOGGER.info("Community database restored successfully from %s", backup_file)
        return True
    except Exception as exc:
        LOGGER.error("Failed to restore community database: %s", exc)
        return False
    finally:
        target_conn.close()
        backup_conn.close()

