from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import CORS_ORIGINS
from backend.core.database import get_books_df
from backend.routers import (
    auth_router,
    home_router,
    book_router,
    author_router,
    genre_router,
    chat_router,
    crawler_router,
    location_router,
    reading_router,
    bookshelf_router,
    recommendation_router,
    community_router,
    book_vision_router,
    media_router,
)

app = FastAPI(
    title="AI Digital Library API",
    description="Multi-platform REST API for AI Digital Library, powered by FastAPI, ChromaDB, and Google Gemini.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware for web/flutter/mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router.router, prefix=api_v1_prefix)
app.include_router(home_router.router, prefix=api_v1_prefix)
app.include_router(book_router.router, prefix=api_v1_prefix)
app.include_router(author_router.router, prefix=api_v1_prefix)
app.include_router(genre_router.router, prefix=api_v1_prefix)
app.include_router(chat_router.router, prefix=api_v1_prefix)
app.include_router(crawler_router.router, prefix=api_v1_prefix)
app.include_router(location_router.router, prefix=api_v1_prefix)
app.include_router(reading_router.router, prefix=api_v1_prefix)
app.include_router(bookshelf_router.router, prefix=api_v1_prefix)
app.include_router(recommendation_router.router, prefix=api_v1_prefix)
app.include_router(community_router.router, prefix=api_v1_prefix)
app.include_router(book_vision_router.router, prefix=api_v1_prefix)
app.include_router(media_router.router, prefix=api_v1_prefix)


# Phục vụ Static Files cho Sách mẫu đọc trực tuyến và Frontend Web
samples_dir = Path("data/sample_books")
if samples_dir.exists():
    app.mount("/samples", StaticFiles(directory=str(samples_dir)), name="sample_books")

frontend_dir = Path("frontend_web")
if frontend_dir.exists():
    app.mount("/static_web", StaticFiles(directory=str(frontend_dir)), name="frontend_web")


@app.get("/", tags=["Frontend Web"])
def serve_index() -> Any:
    index_path = Path("frontend_web/index.html")
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return {
        "message": "Welcome to AI Digital Library API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/web", tags=["Frontend Web"])
def serve_web() -> Any:
    index_path = Path("frontend_web/index.html")
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return {"message": "frontend_web/index.html is not created yet."}


@app.get("/docs-pdf", tags=["Documentation"])
def serve_docs_pdf() -> Any:
    pdf_path = Path("docs/BAO_CAO_DO_AN_AI.pdf")
    if pdf_path.exists():
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=BAO_CAO_DO_AN_AI.pdf"},
        )
    return JSONResponse(status_code=404, content={"detail": "Tệp báo cáo PDF chưa tồn tại."})


@app.get("/api", tags=["Root"])
def api_info() -> dict[str, Any]:
    return {
        "message": "Welcome to AI Digital Library API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check() -> dict[str, Any]:
    books_df = get_books_df()
    total_books = len(books_df)

    vector_count = None
    try:
        from rag_engine import get_library_book_count
        vector_count = get_library_book_count()
    except Exception as e:
        vector_count = f"Unavailable: {str(e)}"

    return {
        "status": "healthy",
        "total_books_csv": total_books,
        "chromadb_vectors": vector_count,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )

