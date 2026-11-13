from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
import pandas as pd

from backend.core.config import (
    BOOKS_CSV_PATH,
    AUTHORS_CSV_PATH,
    GENRES_CSV_PATH,
    USERS_FILE_PATH,
)

# Global locks to ensure thread-safety on writes
csv_write_lock = threading.Lock()
users_write_lock = threading.Lock()

# Cached dataframes with mtime tracking
_cached_mtimes: dict[str, float] = {}
_cached_dfs: dict[str, pd.DataFrame] = {}


def get_file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except (FileNotFoundError, OSError):
        return 0.0


def get_books_df(force_reload: bool = False) -> pd.DataFrame:
    mtime = get_file_mtime(BOOKS_CSV_PATH)
    if force_reload or "books" not in _cached_dfs or _cached_mtimes.get("books") != mtime:
        if BOOKS_CSV_PATH.exists():
            df = pd.read_csv(BOOKS_CSV_PATH).fillna("")
            if "isbn" in df.columns:
                df["isbn"] = df["isbn"].astype(str)
        else:
            df = pd.DataFrame()
        _cached_dfs["books"] = df
        _cached_mtimes["books"] = mtime
    return _cached_dfs["books"].copy()


def get_authors_df(force_reload: bool = False) -> pd.DataFrame:
    mtime = get_file_mtime(AUTHORS_CSV_PATH)
    if force_reload or "authors" not in _cached_dfs or _cached_mtimes.get("authors") != mtime:
        if AUTHORS_CSV_PATH.exists():
            df = pd.read_csv(AUTHORS_CSV_PATH).fillna("")
        else:
            df = pd.DataFrame()
        _cached_dfs["authors"] = df
        _cached_mtimes["authors"] = mtime
    return _cached_dfs["authors"].copy()


def get_genres_df(force_reload: bool = False) -> pd.DataFrame:
    mtime = get_file_mtime(GENRES_CSV_PATH)
    if force_reload or "genres" not in _cached_dfs or _cached_mtimes.get("genres") != mtime:
        if GENRES_CSV_PATH.exists():
            df = pd.read_csv(GENRES_CSV_PATH).fillna("")
        else:
            df = pd.DataFrame()
        _cached_dfs["genres"] = df
        _cached_mtimes["genres"] = mtime
    return _cached_dfs["genres"].copy()


def load_users() -> dict[str, dict[str, Any]]:
    with users_write_lock:
        if not USERS_FILE_PATH.exists():
            return {}
        try:
            with open(USERS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


def save_users(users: dict[str, dict[str, Any]]) -> None:
    with users_write_lock:
        USERS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
