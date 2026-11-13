from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, Query, status

from backend.core.config import BOOKSHELVES_DIR
from backend.core.database import get_books_df
from backend.core.security import get_current_user
from backend.schemas.bookshelf_schema import (
    BookshelfItemCreate,
    BookshelfItemUpdate,
    BookshelfItemResponse,
    BookshelfListResponse,
    BookshelfCheckResponse,
)
from book_service import get_book_by_id

router = APIRouter(prefix="/bookshelf", tags=["Bookshelf"])

BOOKSHELVES_DIR.mkdir(parents=True, exist_ok=True)
_bookshelf_lock = threading.Lock()

VALID_STATUSES = {"favorite", "reading", "completed"}


def _get_user_file(username: str) -> Path:
    # Ensure safe filename
    safe_username = "".join(c for c in username if c.isalnum() or c in ("_", "-"))
    return BOOKSHELVES_DIR / f"{safe_username}.json"


def _load_user_bookshelf(username: str) -> dict[str, Any]:
    file_path = _get_user_file(username)
    with _bookshelf_lock:
        if not file_path.exists():
            return {"username": username, "items": {}}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"username": username, "items": {}}
                if "items" not in data or not isinstance(data["items"], dict):
                    data["items"] = {}
                return data
        except Exception:
            return {"username": username, "items": {}}


def _save_user_bookshelf(username: str, data: dict[str, Any]) -> None:
    file_path = _get_user_file(username)
    with _bookshelf_lock:
        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path.replace(file_path)
        except Exception:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


def _enrich_book_metadata(book_id: str) -> dict[str, Any]:
    books_df = get_books_df()
    rec = get_book_by_id(book_id, books=books_df)
    if not rec:
        return {"book_id": book_id, "title": "Sách không tồn tại"}
    return {
        "book_id": rec.get("book_id", book_id),
        "title": rec.get("title", ""),
        "author": rec.get("author", ""),
        "cover_image": rec.get("cover_image", ""),
        "genre": rec.get("genre", ""),
        "publisher": rec.get("publisher", ""),
        "publish_year": rec.get("publish_year", 0),
        "rating": rec.get("rating", 0.0),
        "reading_available": bool(rec.get("reading_available")),
        "reading_type": rec.get("reading_type", ""),
        "reading_url": rec.get("reading_url", ""),
    }


@router.get("", response_model=BookshelfListResponse)
def get_bookshelf(
    status_filter: str | None = Query(None, alias="status", description="Lọc theo trạng thái: favorite, reading, completed"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BookshelfListResponse:
    username = current_user["username"]
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    result_items: list[BookshelfItemResponse] = []
    for item_id, item in items_dict.items():
        if status_filter and item.get("status") != status_filter:
            continue
        book_meta = _enrich_book_metadata(item.get("book_id", ""))
        result_items.append(
            BookshelfItemResponse(
                id=item_id,
                book_id=item.get("book_id", ""),
                status=item.get("status", "favorite"),
                progress_page=item.get("progress_page", 0),
                total_pages=item.get("total_pages", 0),
                rating=item.get("rating", 0),
                notes=item.get("notes", ""),
                added_at=item.get("added_at", ""),
                updated_at=item.get("updated_at", ""),
                book=book_meta,
            )
        )

    # Sort newest first
    result_items.sort(key=lambda x: x.added_at, reverse=True)
    return BookshelfListResponse(total=len(result_items), items=result_items)


@router.get("/check/{book_id}", response_model=BookshelfCheckResponse)
def check_book_in_bookshelf(
    book_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BookshelfCheckResponse:
    username = current_user["username"]
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    matching_items: list[BookshelfItemResponse] = []
    statuses: list[str] = []

    for item_id, item in items_dict.items():
        if item.get("book_id") == book_id:
            statuses.append(item.get("status", ""))
            book_meta = _enrich_book_metadata(book_id)
            matching_items.append(
                BookshelfItemResponse(
                    id=item_id,
                    book_id=book_id,
                    status=item.get("status", "favorite"),
                    progress_page=item.get("progress_page", 0),
                    total_pages=item.get("total_pages", 0),
                    rating=item.get("rating", 0),
                    notes=item.get("notes", ""),
                    added_at=item.get("added_at", ""),
                    updated_at=item.get("updated_at", ""),
                    book=book_meta,
                )
            )

    return BookshelfCheckResponse(
        book_id=book_id,
        in_bookshelf=len(matching_items) > 0,
        statuses=statuses,
        items=matching_items,
    )


@router.post("", response_model=BookshelfItemResponse, status_code=status.HTTP_201_CREATED)
def add_bookshelf_item(
    item_in: BookshelfItemCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BookshelfItemResponse:
    username = current_user["username"]

    # 1. Validate status
    if item_in.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trạng thái '{item_in.status}' không hợp lệ. Phải là một trong: {', '.join(VALID_STATUSES)}",
        )

    # 2. Validate book existence in library
    books_df = get_books_df()
    book_rec = get_book_by_id(item_in.book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sách với mã '{item_in.book_id}' trong thư viện",
        )

    # 3. Load user's shelf and check duplicate
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    for item_id, existing in items_dict.items():
        if existing.get("book_id") == item_in.book_id and existing.get("status") == item_in.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sách này đã tồn tại trong danh mục '{item_in.status}' của bạn.",
            )

    now_iso = datetime.now().isoformat()
    item_id = f"{item_in.book_id}_{item_in.status}_{uuid.uuid4().hex[:6]}"

    new_item = {
        "id": item_id,
        "book_id": item_in.book_id,
        "status": item_in.status,
        "progress_page": item_in.progress_page,
        "total_pages": item_in.total_pages or book_rec.get("pages", 0) or 0,
        "rating": item_in.rating,
        "notes": item_in.notes,
        "added_at": now_iso,
        "updated_at": now_iso,
    }

    items_dict[item_id] = new_item
    shelf_data["items"] = items_dict
    _save_user_bookshelf(username, shelf_data)

    # Record community activity safely
    try:
        from backend.services.community_service import record_activity
        if item_in.status == "reading":
            record_activity(
                username=username,
                activity_type="reading_started",
                entity_id=item_in.book_id,
                entity_type="book",
                metadata={"book_id": item_in.book_id, "title": book_rec.get("title", "")},
            )
        elif item_in.status == "completed":
            record_activity(
                username=username,
                activity_type="book_completed",
                entity_id=item_in.book_id,
                entity_type="book",
                metadata={"book_id": item_in.book_id, "title": book_rec.get("title", "")},
            )
    except Exception:
        pass

    book_meta = _enrich_book_metadata(item_in.book_id)
    return BookshelfItemResponse(
        id=item_id,
        book_id=new_item["book_id"],
        status=new_item["status"],
        progress_page=new_item["progress_page"],
        total_pages=new_item["total_pages"],
        rating=new_item["rating"],
        notes=new_item["notes"],
        added_at=new_item["added_at"],
        updated_at=new_item["updated_at"],
        book=book_meta,
    )


@router.put("/{item_id}", response_model=BookshelfItemResponse)
def update_bookshelf_item(
    item_id: str,
    update_in: BookshelfItemUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BookshelfItemResponse:
    username = current_user["username"]
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    if item_id not in items_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy mục '{item_id}' trong tủ sách của bạn",
        )

    current_item = items_dict[item_id]

    if update_in.status is not None:
        if update_in.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trạng thái '{update_in.status}' không hợp lệ.",
            )
        # Check duplicate if changing status
        if update_in.status != current_item.get("status"):
            for other_id, other_item in items_dict.items():
                if (
                    other_id != item_id
                    and other_item.get("book_id") == current_item.get("book_id")
                    and other_item.get("status") == update_in.status
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sách này đã tồn tại trong danh mục '{update_in.status}' của bạn.",
                    )
            current_item["status"] = update_in.status

    if update_in.progress_page is not None:
        current_item["progress_page"] = update_in.progress_page
    if update_in.total_pages is not None:
        current_item["total_pages"] = update_in.total_pages
    if update_in.rating is not None:
        current_item["rating"] = update_in.rating
    if update_in.notes is not None:
        current_item["notes"] = update_in.notes

    current_item["updated_at"] = datetime.now().isoformat()
    items_dict[item_id] = current_item
    shelf_data["items"] = items_dict
    _save_user_bookshelf(username, shelf_data)

    # Record community activity safely
    try:
        from backend.services.community_service import record_activity
        if update_in.status == "reading":
            record_activity(
                username=username,
                activity_type="reading_started",
                entity_id=current_item["book_id"],
                entity_type="book",
                metadata={"book_id": current_item["book_id"], "title": book_meta.get("title", "") if "book_meta" in locals() else ""},
            )
        elif update_in.status == "completed":
            record_activity(
                username=username,
                activity_type="book_completed",
                entity_id=current_item["book_id"],
                entity_type="book",
                metadata={"book_id": current_item["book_id"], "title": book_meta.get("title", "") if "book_meta" in locals() else ""},
            )
    except Exception:
        pass

    book_meta = _enrich_book_metadata(current_item.get("book_id", ""))
    return BookshelfItemResponse(
        id=item_id,
        book_id=current_item["book_id"],
        status=current_item["status"],
        progress_page=current_item["progress_page"],
        total_pages=current_item["total_pages"],
        rating=current_item["rating"],
        notes=current_item["notes"],
        added_at=current_item["added_at"],
        updated_at=current_item["updated_at"],
        book=book_meta,
    )


@router.delete("/{item_id}")
def delete_bookshelf_item(
    item_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    username = current_user["username"]
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    if item_id not in items_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy mục '{item_id}' trong tủ sách",
        )

    del items_dict[item_id]
    shelf_data["items"] = items_dict
    _save_user_bookshelf(username, shelf_data)

    return {"success": True, "message": "Đã xóa sách khỏi tủ sách thành công"}


@router.delete("/book/{book_id}")
def delete_book_from_bookshelf(
    book_id: str,
    status_filter: str | None = Query(None, alias="status", description="Xóa trạng thái cụ thể hoặc xóa tất cả"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    username = current_user["username"]
    shelf_data = _load_user_bookshelf(username)
    items_dict = shelf_data.get("items", {})

    to_delete = [
        item_id
        for item_id, item in items_dict.items()
        if item.get("book_id") == book_id and (status_filter is None or item.get("status") == status_filter)
    ]

    if not to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sách '{book_id}' không có trong tủ sách của bạn",
        )

    for item_id in to_delete:
        del items_dict[item_id]

    shelf_data["items"] = items_dict
    _save_user_bookshelf(username, shelf_data)

    return {
        "success": True,
        "deleted_count": len(to_delete),
        "message": f"Đã xóa {len(to_delete)} mục khỏi tủ sách",
    }

