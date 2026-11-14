from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CrawlSearchRequest(BaseModel):
    query: str = Field("", description="Keywords or ISBN to search for")
    author: str = Field("", description="Author name")
    subject: str = Field("", description="Subject or Genre")
    isbn: str = Field("", description="ISBN code")
    language: str = Field("", description="Language code: vie, eng, fra...")
    year_from: int = Field(0, description="From year")
    year_to: int = Field(0, description="To year")
    source: str = Field("all", description="Source to search: all, openlibrary, google_books, gutenberg, internet_archive, europeana, itunes")
    limit: int = Field(10, ge=1, le=100, description="Max results per source")


class CrawlBookCandidate(BaseModel):
    title: str = ""
    author: str = ""
    isbn: str = ""
    publisher: str = ""
    year: Any = None
    pages: Any = None
    language: str = ""
    description: str = ""
    cover_url: str = ""
    reading_available: Any = False
    reading_type: str = ""
    reading_url: str = ""
    source: str = ""
    is_duplicate: bool = False
    matched_by: str = ""
    matched_book_id: str = ""
    genre: str = ""
    tags: str = ""
    target_audience: str = ""
    mood: str = ""
    difficulty: str = ""
    summary: str = ""
    local_file: str = ""
    purchase_url: str = ""
    library_url: str = ""
    rating: Any = None
    featured: Any = False
    format: str = ""


class CrawlSearchResponse(BaseModel):
    query: str
    source: str
    total_found: int
    results: list[dict[str, Any]]


class CrawlImportRequest(BaseModel):
    candidate: dict[str, Any] = Field(..., description="Normalized book record to import into library")
    upsert_chroma: bool = Field(True, description="Whether to ingest new vector into ChromaDB immediately")


class CrawlImportResponse(BaseModel):
    success: bool
    message: str
    book_id: str | None = None
    vector_indexed: bool = False
    vector_status: dict[str, Any] | None = None


class CrawlBatchImportItemResult(BaseModel):
    title: str
    book_id: str | None = None
    success: bool
    message: str
    vector_indexed: bool = False


class CrawlBatchImportRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1, description="List of book candidates to import")
    upsert_chroma: bool = Field(True, description="Whether to ingest new vectors into ChromaDB immediately")


class CrawlBatchImportResponse(BaseModel):
    total_requested: int
    imported_count: int
    skipped_count: int
    results: list[CrawlBatchImportItemResult]
    vector_status: dict[str, Any] | None = None


class SyncChromaResponse(BaseModel):
    success: bool
    synced_count: int
    total_unindexed: int = 0
    failed_count: int = 0
    message: str
    synced_titles: list[str] = []
    total_csv_books: int = 0
    total_chroma_vectors: int = 0
    missing_vectors_count: int = 0
    is_synced: bool = True
    timestamp: str = ""
