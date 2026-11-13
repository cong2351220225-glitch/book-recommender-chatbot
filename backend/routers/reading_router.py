from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse

from backend.core.config import DATA_DIR
from backend.core.database import get_books_df
from backend.core.security import get_current_user, get_current_user_optional
from backend.schemas.reading_schema import (
    ReadingProgressCreate,
    ReadingProgressResponse,
    ReadingDocInfoResponse,
)
from backend.routers.bookshelf_router import _load_user_bookshelf, _save_user_bookshelf
from book_service import get_book_by_id
from reading_service import (
    can_read,
    reading_status,
    validate_local_file,
    get_book_reading_file,
)

router = APIRouter(prefix="/reading", tags=["Reading"])

READING_PROGRESS_DIR = DATA_DIR / "reading_progress"
READING_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
_reading_lock = threading.Lock()


def _sanitize_book_id(book_id: str) -> str:
    cleaned = book_id.strip()
    if not cleaned or not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã sách không hợp lệ hoặc chứa ký tự không an toàn",
        )
    return cleaned


def _load_user_progress(username: str) -> dict[str, Any]:
    file_path = READING_PROGRESS_DIR / f"{username}.json"
    with _reading_lock:
        if not file_path.exists():
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}


def _save_user_progress(username: str, data: dict[str, Any]) -> None:
    file_path = READING_PROGRESS_DIR / f"{username}.json"
    with _reading_lock:
        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path.replace(file_path)
        except Exception:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("/status/{book_id}")
def get_reading_status(book_id: str) -> dict[str, Any]:
    clean_id = _sanitize_book_id(book_id)
    books_df = get_books_df()
    book_rec = get_book_by_id(clean_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{clean_id}' not found",
        )

    file_path = get_book_reading_file(book_rec)
    has_file = file_path is not None
    fmt = file_path.suffix.lstrip(".").lower() if file_path else ""

    return {
        "book_id": clean_id,
        "title": book_rec.get("title", ""),
        "reading_available": has_file or bool(book_rec.get("reading_available")),
        "reading_type": fmt or book_rec.get("reading_type", ""),
        "reading_url": f"/api/v1/reading/file/{clean_id}" if has_file else book_rec.get("reading_url", ""),
        "can_read_locally": has_file,
        "status_label": reading_status(book_rec),
    }


@router.get("/file/{book_id}")
def get_reading_file(book_id: str):
    clean_id = _sanitize_book_id(book_id)
    books_df = get_books_df()
    book_rec = get_book_by_id(clean_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{clean_id}' not found",
        )

    file_path = get_book_reading_file(book_rec)
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tài liệu đọc cho sách '{clean_id}' không tồn tại hoặc chưa được cập nhật",
        )

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "application/epub+zip"
    return FileResponse(
        path=str(file_path),
        filename=f"{clean_id}{file_path.suffix}",
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{clean_id}{file_path.suffix}"',
        },
    )


@router.get("/info/{book_id}", response_model=ReadingDocInfoResponse)
def get_reading_doc_info(
    book_id: str,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ReadingDocInfoResponse:
    clean_id = _sanitize_book_id(book_id)
    books_df = get_books_df()
    book_rec = get_book_by_id(clean_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{clean_id}' not found",
        )

    file_path = get_book_reading_file(book_rec)
    has_file = file_path is not None
    fmt = file_path.suffix.lstrip(".").lower() if file_path else "none"
    size_bytes = file_path.stat().st_size if file_path and file_path.exists() else 0

    saved_prog: ReadingProgressResponse | None = None
    if current_user:
        username = current_user["username"]
        all_prog = _load_user_progress(username)
        if clean_id in all_prog:
            item = all_prog[clean_id]
            saved_prog = ReadingProgressResponse(
                book_id=clean_id,
                current_page=item.get("current_page", 1),
                total_pages=item.get("total_pages", 1),
                progress_percent=item.get("progress_percent", 0.0),
                last_read_location=item.get("last_read_location", ""),
                updated_at=item.get("updated_at", ""),
            )

    return ReadingDocInfoResponse(
        book_id=clean_id,
        title=book_rec.get("title", ""),
        author=book_rec.get("author", ""),
        can_read=has_file,
        format=fmt,
        file_size_bytes=size_bytes,
        file_url=f"/api/v1/reading/file/{clean_id}" if has_file else "",
        saved_progress=saved_prog,
    )


@router.get("/progress/{book_id}", response_model=ReadingProgressResponse)
def get_reading_progress(
    book_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReadingProgressResponse:
    clean_id = _sanitize_book_id(book_id)
    username = current_user["username"]
    all_prog = _load_user_progress(username)

    if clean_id not in all_prog:
        # Default starting position
        return ReadingProgressResponse(
            book_id=clean_id,
            current_page=1,
            total_pages=1,
            progress_percent=0.0,
            last_read_location="Trang 1",
            updated_at=datetime.now().isoformat(),
        )

    item = all_prog[clean_id]
    return ReadingProgressResponse(
        book_id=clean_id,
        current_page=item.get("current_page", 1),
        total_pages=item.get("total_pages", 1),
        progress_percent=item.get("progress_percent", 0.0),
        last_read_location=item.get("last_read_location", "Trang 1"),
        updated_at=item.get("updated_at", datetime.now().isoformat()),
    )


@router.post("/progress", response_model=ReadingProgressResponse)
def save_reading_progress(
    prog_in: ReadingProgressCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ReadingProgressResponse:
    clean_id = _sanitize_book_id(prog_in.book_id)
    username = current_user["username"]

    now_iso = datetime.now().isoformat()
    pct = round(
        (prog_in.current_page / prog_in.total_pages) * 100.0 if prog_in.total_pages > 0 else 0.0,
        1,
    )
    if pct > 100.0:
        pct = 100.0

    entry = {
        "book_id": clean_id,
        "current_page": prog_in.current_page,
        "total_pages": prog_in.total_pages,
        "progress_percent": pct,
        "last_read_location": prog_in.last_read_location or f"Trang {prog_in.current_page}",
        "updated_at": now_iso,
    }

    # 1. Save reading progress
    all_prog = _load_user_progress(username)
    all_prog[clean_id] = entry
    _save_user_progress(username, all_prog)

    # 2. Sync to Personal Bookshelf
    try:
        shelf_data = _load_user_bookshelf(username)
        items_dict = shelf_data.get("items", {})
        synced = False
        for item_id, item in items_dict.items():
            if item.get("book_id") == clean_id and item.get("status") in {"reading", "favorite"}:
                item["progress_page"] = prog_in.current_page
                item["total_pages"] = prog_in.total_pages
                item["updated_at"] = now_iso
                synced = True

        if not synced:
            # Auto-add to "reading" in bookshelf if not present
            new_item_id = f"{clean_id}_reading_auto"
            items_dict[new_item_id] = {
                "id": new_item_id,
                "book_id": clean_id,
                "status": "reading",
                "progress_page": prog_in.current_page,
                "total_pages": prog_in.total_pages,
                "rating": 0,
                "notes": "Tự động ghi nhận từ Trình đọc sách số",
                "added_at": now_iso,
                "updated_at": now_iso,
            }

        shelf_data["items"] = items_dict
        _save_user_bookshelf(username, shelf_data)
    except Exception:
        pass

    # 3. Record community activity safely
    try:
        from backend.services.community_service import record_activity
        b_rec = get_book_by_id(clean_id, books=get_books_df())
        b_title = b_rec.get("title", "") if b_rec else ""

        if prog_in.current_page == 1 or not all_prog or clean_id not in all_prog:
            record_activity(
                username=username,
                activity_type="reading_started",
                entity_id=clean_id,
                entity_type="book",
                metadata={"book_id": clean_id, "title": b_title},
            )
        if pct >= 100.0 or (prog_in.total_pages > 0 and prog_in.current_page >= prog_in.total_pages):
            record_activity(
                username=username,
                activity_type="book_completed",
                entity_id=clean_id,
                entity_type="book",
                metadata={"book_id": clean_id, "title": b_title},
            )
    except Exception:
        pass

    return ReadingProgressResponse(
        book_id=clean_id,
        current_page=entry["current_page"],
        total_pages=entry["total_pages"],
        progress_percent=entry["progress_percent"],
        last_read_location=entry["last_read_location"],
        updated_at=entry["updated_at"],
    )
