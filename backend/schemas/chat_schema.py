from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question or input")
    session_id: str | None = Field(None, description="Optional conversation session ID")
    top_k: int = Field(3, ge=1, le=10, description="Top K books to retrieve for context")
    reader_profile: dict[str, Any] | None = Field(None, description="User preference profile")


class ChatResponse(BaseModel):
    answer: str
    books: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    intent: str
    session_id: str
    reader_profile: dict[str, Any] | None = None


class ChatMessageItem(BaseModel):
    role: str
    content: str
    timestamp: str | None = None
    sources: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]


class ChatSessionItem(BaseModel):
    id: str
    title: str
    timestamp: str
    message_count: int = 0
    last_message: str = ""


class ChatSessionsResponse(BaseModel):
    sessions: list[ChatSessionItem]


class DeleteSessionResponse(BaseModel):
    status: str = "deleted"
    session_id: str


class RagConfigResponse(BaseModel):
    vector_count: int
    default_top_k: int = 3
    max_top_k: int = 10
    min_top_k: int = 1
    collection_name: str = "books_collection"
