from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, status

from backend.core.config import BOOKS_CSV_PATH, CHROMA_PATH, COLLECTION_NAME
from backend.core.database import get_books_df, csv_write_lock
from backend.core.security import require_admin
from backend.schemas.crawler_schema import (
    CrawlSearchRequest,
    CrawlSearchResponse,
    CrawlImportRequest,
    CrawlImportResponse,
    CrawlBatchImportRequest,
    CrawlBatchImportResponse,
    CrawlBatchImportItemResult,
    SyncChromaResponse,
)
from crawler_service import (
    crawl_and_prepare,
    save_books_to_csv,
    ingest_books_to_chroma,
    get_unindexed_books,
    sync_unindexed_books_to_chroma,
    SOURCE_MAP,
)
from config import GEMINI_API_KEY

router = APIRouter(prefix="/crawler", tags=["AI Crawler"])

_sync_lock = threading.Lock()
CHROMA_SYNC_META_PATH = Path("data/chroma_sync_meta.json")


def _get_sync_meta() -> dict[str, Any]:
    if CHROMA_SYNC_META_PATH.exists():
        try:
            with open(CHROMA_SYNC_META_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_sync_meta(meta: dict[str, Any]) -> None:
    try:
        CHROMA_SYNC_META_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CHROMA_SYNC_META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@router.get("/sources")
def get_sources() -> dict[str, Any]:
    return {
        "sources": [
            {"id": "all", "name": "Tất cả các nguồn", "description": "Tìm kiếm đồng thời trên 6 nguồn chính thống"},
            {"id": "openlibrary", "name": "Open Library", "description": "Kho sách mở phi lợi nhuận toàn cầu"},
            {"id": "google_books", "name": "Google Books", "description": "Kho dữ liệu sách khổng lồ của Google"},
            {"id": "gutenberg", "name": "Project Gutenberg", "description": "Kho sách điện tử tự do, miễn phí bản quyền"},
            {"id": "internet_archive", "name": "Internet Archive", "description": "Thư viện số lưu trữ tài liệu thế giới"},
            {"id": "europeana", "name": "Europeana", "description": "Di sản số châu Âu (nghệ thuật, văn học)"},
            {"id": "itunes", "name": "Apple Books / iTunes", "description": "Kho ấn bản số chính thống từ Apple"},
        ]
    }


@router.post("/search", response_model=CrawlSearchResponse)
def search_crawler_sources(req: CrawlSearchRequest) -> CrawlSearchResponse:
    q = (req.query or "").strip()
    a = (req.author or "").strip()
    s = (req.subject or "").strip()
    i = (req.isbn or "").strip()
    if not q and not a and not s and not i:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập ít nhất một từ khóa, tên tác giả, chủ đề hoặc mã ISBN.",
        )
    try:
        results = crawl_and_prepare(
            source=req.source,
            query=q,
            author=a,
            subject=s,
            isbn=i,
            language=(req.language or "").strip(),
            year_from=req.year_from,
            year_to=req.year_to,
            limit=req.limit,
            existing_df=get_books_df(),
        )
        display_query = q or a or s or i
        return CrawlSearchResponse(
            query=display_query,
            source=req.source,
            total_found=len(results),
            results=results,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawler search failed: {str(e)}",
        )


@router.post("/import", response_model=CrawlImportResponse)
def import_crawler_book(
    req: CrawlImportRequest,
    current_admin: dict[str, Any] = Depends(require_admin),
) -> CrawlImportResponse:
    candidate = dict(req.candidate) if req.candidate else {}
    if not candidate or not candidate.get("title"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book candidate must contain at least a 'title'",
        )

    with csv_write_lock:
        stats = save_books_to_csv([candidate], csv_path=BOOKS_CSV_PATH)
        if stats.get("saved", 0) == 0:
            return CrawlImportResponse(
                success=False,
                message="Cuốn sách này đã tồn tại trong thư viện (trùng ISBN hoặc tiêu đề & tác giả).",
                book_id=None,
                vector_indexed=False,
            )

        book_id = candidate.get("book_id")

        vector_indexed = False
        if req.upsert_chroma and GEMINI_API_KEY:
            try:
                chroma_res = ingest_books_to_chroma(
                    books_to_ingest=[candidate],
                    gemini_api_key=GEMINI_API_KEY,
                    chroma_path=CHROMA_PATH,
                )
                vector_indexed = chroma_res.get("upserted", 0) > 0
            except Exception:
                vector_indexed = False

        # Invalidate cache so subsequent reads see the new record
        get_books_df(force_reload=True)

        return CrawlImportResponse(
            success=True,
            message=f"Đã nhập thành công sách '{candidate.get('title')}' vào thư viện.",
            book_id=book_id,
            vector_indexed=vector_indexed,
        )


@router.post("/batch-import", response_model=CrawlBatchImportResponse)
def batch_import_crawler_books(
    req: CrawlBatchImportRequest,
    current_admin: dict[str, Any] = Depends(require_admin),
) -> CrawlBatchImportResponse:
    if not req.candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách sách nhập không được để trống",
        )

    results: list[CrawlBatchImportItemResult] = []
    saved_candidates: list[dict[str, Any]] = []

    with csv_write_lock:
        for raw_cand in req.candidates:
            cand = dict(raw_cand)
            title = str(cand.get("title", "")).strip()
            if not title:
                results.append(
                    CrawlBatchImportItemResult(
                        title="Không rõ tiêu đề",
                        book_id=None,
                        success=False,
                        message="Thiếu tiêu đề sách",
                        vector_indexed=False,
                    )
                )
                continue

            stats = save_books_to_csv([cand], csv_path=BOOKS_CSV_PATH)
            if stats.get("saved", 0) > 0:
                book_id = cand.get("book_id")
                saved_candidates.append(cand)
                results.append(
                    CrawlBatchImportItemResult(
                        title=title,
                        book_id=book_id,
                        success=True,
                        message=f"Đã nhập thành công vào thư viện (Mã: {book_id})",
                        vector_indexed=False,
                    )
                )
            else:
                results.append(
                    CrawlBatchImportItemResult(
                        title=title,
                        book_id=None,
                        success=False,
                        message="Bỏ qua do đã tồn tại trong thư viện (trùng tiêu đề hoặc ISBN)",
                        vector_indexed=False,
                    )
                )

        if saved_candidates and req.upsert_chroma and GEMINI_API_KEY:
            try:
                chroma_res = ingest_books_to_chroma(
                    books_to_ingest=saved_candidates,
                    gemini_api_key=GEMINI_API_KEY,
                    chroma_path=CHROMA_PATH,
                )
                if chroma_res.get("upserted", 0) > 0:
                    for res in results:
                        if res.success:
                            res.vector_indexed = True
            except Exception:
                pass

        if saved_candidates:
            get_books_df(force_reload=True)

    imported_count = len(saved_candidates)
    skipped_count = len(req.candidates) - imported_count

    return CrawlBatchImportResponse(
        total_requested=len(req.candidates),
        imported_count=imported_count,
        skipped_count=skipped_count,
        results=results,
    )


@router.get("/unindexed")
def list_unindexed_books(
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    unindexed = get_unindexed_books(
        csv_path=BOOKS_CSV_PATH,
        chroma_path=CHROMA_PATH,
    )
    books_df = get_books_df()
    total_books = len(books_df)
    unindexed_count = len(unindexed)
    indexed_count = max(0, total_books - unindexed_count)
    meta = _get_sync_meta()

    return {
        "count": unindexed_count,
        "unindexed_books": unindexed,
        "total_books": total_books,
        "indexed_count": indexed_count,
        "failed_count": meta.get("last_failed_count", 0),
        "last_synced_at": meta.get("last_synced_at"),
        "collection_name": COLLECTION_NAME,
        "embedding_model": "gemini-embedding-2",
    }


@router.post("/sync-unindexed", response_model=SyncChromaResponse)
def sync_unindexed_vectors(
    current_admin: dict[str, Any] = Depends(require_admin),
) -> SyncChromaResponse:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEY is not configured",
        )

    # Prevent concurrent syncs
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tiến trình đồng bộ ChromaDB đang được thực hiện bởi một phiên khác. Vui lòng thử lại sau.",
        )

    try:
        with csv_write_lock:
            unindexed_before = get_unindexed_books(
                csv_path=BOOKS_CSV_PATH,
                chroma_path=CHROMA_PATH,
            )
            total_unindexed = len(unindexed_before)

            if total_unindexed == 0:
                _save_sync_meta({
                    "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_synced_count": 0,
                    "last_failed_count": 0,
                    "total_unindexed": 0,
                })
                return SyncChromaResponse(
                    success=True,
                    synced_count=0,
                    total_unindexed=0,
                    failed_count=0,
                    message="Tất cả các sách trong thư viện đều đã được đồng bộ vector ChromaDB.",
                )

            sync_result = sync_unindexed_books_to_chroma(
                gemini_api_key=GEMINI_API_KEY,
                csv_path=BOOKS_CSV_PATH,
                chroma_path=CHROMA_PATH,
            )
            synced_count = sync_result.get("upserted", sync_result.get("synced", 0)) if isinstance(sync_result, dict) else int(sync_result)
            failed_count = sync_result.get("failed", 0) if isinstance(sync_result, dict) else 0

            _save_sync_meta({
                "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_synced_count": synced_count,
                "last_failed_count": failed_count,
                "total_unindexed": total_unindexed,
            })

            fail_msg = f" ({failed_count} sách lỗi)" if failed_count > 0 else ""
            return SyncChromaResponse(
                success=True,
                synced_count=synced_count,
                total_unindexed=total_unindexed,
                failed_count=failed_count,
                message=f"Đã đồng bộ thành công {synced_count}/{total_unindexed} sách vào ChromaDB.{fail_msg}",
            )
    finally:
        _sync_lock.release()
