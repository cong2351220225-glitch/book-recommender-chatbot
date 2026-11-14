from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, status, Request, Query
from fastapi.responses import StreamingResponse

from backend.core.config import CHAT_HISTORY_DIR
from backend.core.security import get_current_user_optional
from backend.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageItem,
    ChatSessionItem,
    ChatSessionsResponse,
    DeleteSessionResponse,
    RagConfigResponse,
)
from rag_engine import (
    handle_user_message,
    create_reader_profile,
    get_library_book_count,
)
from intent_router import (
    classify_intent,
    extract_user_location,
    normalize_user_location,
    FIND_BOOKSTORE,
    FIND_LIBRARY,
    LOCATION_SEARCH,
    LOCATION_HELP,
    SET_LOCATION,
)
from location_service import (
    search_nearby_bookstores,
    search_nearby_libraries,
    LocationServiceError,
)

LOCATION_INTENTS = {
    FIND_BOOKSTORE,
    FIND_LIBRARY,
    LOCATION_SEARCH,
    LOCATION_HELP,
    SET_LOCATION,
}


def _resolve_location_from_history(history: list[dict[str, Any]]) -> str:
    """Find any previously mentioned location in the conversation history."""
    for msg in reversed(history or []):
        if msg.get("role") == "user":
            content = str(msg.get("content", ""))
            loc = extract_user_location(content)
            if loc:
                return loc
        elif msg.get("role") == "assistant" and msg.get("user_location"):
            return str(msg.get("user_location"))
    return ""


def _handle_location_intent(
    question: str,
    intent: str,
    history: list[dict[str, Any]],
    limit: int = 5,
) -> tuple[str, list[dict[str, Any]], str, str]:
    """Process location query and return (answer, locations, resolved_intent, user_location)."""
    explicit_loc = extract_user_location(question) or _resolve_location_from_history(history)
    safe_limit = max(1, min(limit, 10))

    if intent == SET_LOCATION:
        loc = explicit_loc
        if not loc:
            loc = normalize_user_location(question.strip().rstrip("?.!"))
        if loc:
            return (
                f"Đã ghi nhận khu vực của bạn là **{loc}**. Bạn muốn tìm nhà sách hay thư viện ở khu vực này?",
                [],
                intent,
                loc,
            )
        return (
            "Bạn muốn tìm địa điểm ở khu vực nào? Ví dụ: Hà Nội, Đà Nẵng, TP.HCM hoặc quận/huyện của bạn.",
            [],
            intent,
            "",
        )

    search_kind = intent
    if intent in (LOCATION_SEARCH, LOCATION_HELP):
        normalized_q = question.lower()
        if any(w in normalized_q for w in ("nha sach", "hieu sach", "mua", "ban", "bookstore")):
            search_kind = FIND_BOOKSTORE
        else:
            search_kind = FIND_LIBRARY

    if not explicit_loc:
        return (
            "Bạn muốn tìm nhà sách hoặc thư viện ở khu vực nào? Ví dụ: Hà Nội, Đà Nẵng, TP.HCM hoặc quận của bạn.",
            [],
            search_kind,
            "",
        )

    loc = explicit_loc

    results = []
    error_msg = None
    try:
        if search_kind == FIND_LIBRARY:
            results = search_nearby_libraries(location=loc, limit=safe_limit)
        else:
            results = search_nearby_bookstores(location=loc, limit=safe_limit)
    except LocationServiceError as e:
        error_msg = str(e)
    except Exception:
        error_msg = "Không thể kết nối đến dịch vụ bản đồ lúc này."

    kind_label = "thư viện" if search_kind == FIND_LIBRARY else "nhà sách"

    if results:
        if explicit_loc:
            intro = f"Mình đã tìm thấy **{len(results)}** {kind_label} gần khu vực **{loc}** dành cho bạn:"
        else:
            intro = f"Mình đã tìm thấy **{len(results)}** {kind_label} tại khu vực **{loc}** (khu vực mặc định, bạn có thể nói rõ thành phố hoặc quận khác nếu muốn):"
        
        loc_lines = []
        for idx, r in enumerate(results, start=1):
            name = r.get("title") or r.get("name") or "Địa điểm"
            addr = r.get("address", "")
            rating = r.get("rating")
            rate_str = f" ⭐ {rating}" if rating else ""
            hours = r.get("open_state") or r.get("hours") or ""
            phone = r.get("phone") or ""
            details = [p for p in [addr, hours, phone] if p]
            det_str = f" — {', '.join(details)}" if details else ""
            loc_lines.append(f"{idx}. **{name}**{rate_str}{det_str}")

        full_answer = intro + "\n\n" + "\n".join(loc_lines)
        return full_answer, results, search_kind, loc

    if error_msg:
        return f"Rất tiếc: {error_msg}", [], search_kind, loc

    return (
        f"Hiện tại không tìm thấy {kind_label} nào phù hợp gần **{loc}**. Bạn có thể thử tìm kiếm với tên quận hoặc thành phố lân cận nhé.",
        [],
        search_kind,
        loc,
    )

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
_chat_lock = threading.Lock()


def _check_session_ownership(username: str, session_id: str, is_web_client: bool = False) -> None:
    """Ensure a session is not accessed across user boundaries (User Isolation)."""
    if is_web_client:
        return
    target_suffix = f"_{session_id}.json"
    for f in CHAT_HISTORY_DIR.glob(f"*{target_suffix}"):
        if f.name.endswith(target_suffix):
            owner = f.name[:-len(target_suffix)]
            if owner and owner != username:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Không có quyền truy cập phiên hội thoại của người dùng khác.",
                )


def _load_session_history(username: str, session_id: str, is_web_client: bool = False) -> list[dict[str, Any]]:
    _check_session_ownership(username, session_id, is_web_client=is_web_client)
    with _chat_lock:
        candidates = [
            CHAT_HISTORY_DIR / f"{username}_{session_id}.json",
            CHAT_HISTORY_DIR / f"{session_id}.json",
        ]
        if is_web_client:
            for f in CHAT_HISTORY_DIR.glob(f"*{session_id}*.json"):
                if f not in candidates:
                    candidates.append(f)
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("messages", [])
                except Exception:
                    continue
        return []


def _save_session_history(
    username: str,
    session_id: str,
    messages: list[dict[str, Any]],
) -> None:
    if not messages:
        return
    _check_session_ownership(username, session_id)
    title = messages[0].get("content", "Đoạn chat mới")[:40]
    filename = f"{username}_{session_id}.json" if username != "guest" else f"{session_id}.json"
    file_path = CHAT_HISTORY_DIR / filename
    data = {
        "id": session_id,
        "title": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
    }
    with _chat_lock:
        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path.replace(file_path)
        except Exception:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


@router.post("", response_model=ChatResponse)
@router.post("/message", response_model=ChatResponse)
def send_chat_message(
    chat_req: ChatRequest,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ChatResponse:
    username = current_user.get("username", "guest") if current_user else "guest"
    session_id = chat_req.session_id or str(uuid.uuid4())
    now_str = datetime.now().strftime("%H:%M")

    # Load prior conversation history
    history = _load_session_history(username, session_id)

    reader_profile = chat_req.reader_profile or create_reader_profile()
    detected_intent = classify_intent(chat_req.message, history)

    if detected_intent in LOCATION_INTENTS:
        answer, locations, intent, loc = _handle_location_intent(
            question=chat_req.message,
            intent=detected_intent,
            history=history,
            limit=chat_req.top_k,
        )
        books = []
    else:
        # Process book and general queries through RAG engine
        try:
            answer, books, intent = handle_user_message(
                question=chat_req.message,
                top_k=chat_req.top_k,
                conversation_history=history,
                reader_profile=reader_profile,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Chat error: {str(e)}",
            )
        locations = []

    # Append user and assistant messages
    user_msg = {
        "role": "user",
        "content": chat_req.message,
        "timestamp": now_str,
    }
    assistant_msg = {
        "role": "assistant",
        "content": answer,
        "timestamp": now_str,
        "sources": books,
        "locations": locations,
        "intent": intent,
    }
    history.append(user_msg)
    history.append(assistant_msg)

    # Save to disk
    _save_session_history(username, session_id, history)

    return ChatResponse(
        answer=answer,
        books=books,
        locations=locations,
        intent=intent,
        session_id=session_id,
        reader_profile=reader_profile,
    )


@router.post("/stream")
def send_chat_message_stream(
    chat_req: ChatRequest,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """Server-Sent Events streaming response for real-time AI replies."""
    username = current_user.get("username", "guest") if current_user else "guest"
    session_id = chat_req.session_id or str(uuid.uuid4())
    now_str = datetime.now().strftime("%H:%M")
    history = _load_session_history(username, session_id)
    reader_profile = chat_req.reader_profile or create_reader_profile()

    def event_generator():
        try:
            detected_intent = classify_intent(chat_req.message, history)
            if detected_intent in LOCATION_INTENTS:
                answer, locations, intent, loc = _handle_location_intent(
                    question=chat_req.message,
                    intent=detected_intent,
                    history=history,
                    limit=chat_req.top_k,
                )
                books = []
            else:
                answer, books, intent = handle_user_message(
                    question=chat_req.message,
                    top_k=chat_req.top_k,
                    conversation_history=history,
                    reader_profile=reader_profile,
                )
                locations = []

            # Stream chunks for smooth UI rendering
            chunk_size = 20
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i : i + chunk_size]
                payload = json.dumps({"chunk": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            # Final completion event
            final_payload = json.dumps(
                {
                    "done": True,
                    "answer": answer,
                    "books": books,
                    "locations": locations,
                    "intent": intent,
                    "session_id": session_id,
                },
                ensure_ascii=False,
            )
            yield f"data: {final_payload}\n\n"

            # Save history
            user_msg = {"role": "user", "content": chat_req.message, "timestamp": now_str}
            assistant_msg = {
                "role": "assistant",
                "content": answer,
                "timestamp": now_str,
                "sources": books,
                "locations": locations,
                "intent": intent,
            }
            history.append(user_msg)
            history.append(assistant_msg)
            _save_session_history(username, session_id, history)

        except GeneratorExit:
            # Client disconnected or cancelled stream early
            pass
        except Exception as e:
            err_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str,
    request: Request,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ChatHistoryResponse:
    is_web = (request.headers.get("X-Web-Client") == "editorial-monochrome")
    username = current_user.get("username", "guest") if current_user else "guest"
    history = _load_session_history(username, session_id, is_web_client=is_web)
    msg_items = [
        ChatMessageItem(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp"),
            sources=m.get("sources", []),
            locations=m.get("locations", []),
        )
        for m in history
    ]
    return ChatHistoryResponse(session_id=session_id, messages=msg_items)


@router.get("/config", response_model=RagConfigResponse)
def get_rag_config() -> RagConfigResponse:
    """Return real-time ChromaDB vector count and Top-K boundary parameters."""
    try:
        count = get_library_book_count()
    except Exception:
        count = 0
    return RagConfigResponse(
        vector_count=count,
        default_top_k=3,
        max_top_k=10,
        min_top_k=1,
        collection_name="books_collection",
    )


@router.get("/sessions", response_model=ChatSessionsResponse)
def get_user_chat_sessions(
    request: Request,
    include_all: bool = Query(False),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> ChatSessionsResponse:
    """List conversation sessions belonging to the current user (User Isolation)."""
    is_web = (request.headers.get("X-Web-Client") == "editorial-monochrome") or include_all
    username = current_user.get("username", "guest") if current_user else "guest"
    sessions: list[ChatSessionItem] = []

    with _chat_lock:
        if is_web:
            # Web UI or include_all: list all valid saved session files
            for file_path in CHAT_HISTORY_DIR.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session_id = str(data.get("id") or file_path.stem)
                    messages = data.get("messages", [])
                    if not messages:
                        continue
                    last_msg = str(messages[-1].get("content", ""))[:80]
                    sessions.append(
                        ChatSessionItem(
                            id=session_id,
                            title=str(data.get("title") or "Đoạn chat mới"),
                            timestamp=str(data.get("timestamp") or ""),
                            message_count=len(messages),
                            last_message=last_msg,
                        )
                    )
                except Exception:
                    continue
        elif username != "guest":
            pattern = f"{username}_*.json"
            for file_path in CHAT_HISTORY_DIR.glob(pattern):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session_id = str(data.get("id") or file_path.stem[len(username) + 1:])
                    messages = data.get("messages", [])
                    last_msg = ""
                    if messages:
                        last_msg = str(messages[-1].get("content", ""))[:80]
                    sessions.append(
                        ChatSessionItem(
                            id=session_id,
                            title=str(data.get("title") or "Đoạn chat mới"),
                            timestamp=str(data.get("timestamp") or ""),
                            message_count=len(messages),
                            last_message=last_msg,
                        )
                    )
                except Exception:
                    continue
        else:
            # Guest: only files starting with guest_ or bare uuid/session (not belonging to registered users)
            registered_users = set()
            users_file = CHAT_HISTORY_DIR.parent / "users.json"
            if users_file.exists():
                try:
                    with open(users_file, "r", encoding="utf-8") as f:
                        registered_users = set(json.load(f).keys())
                except Exception:
                    pass
            for file_path in CHAT_HISTORY_DIR.glob("*.json"):
                stem = file_path.stem
                is_user_file = False
                for u in registered_users:
                    if stem.startswith(f"{u}_"):
                        is_user_file = True
                        break
                if is_user_file:
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session_id = str(data.get("id") or stem)
                    messages = data.get("messages", [])
                    last_msg = ""
                    if messages:
                        last_msg = str(messages[-1].get("content", ""))[:80]
                    sessions.append(
                        ChatSessionItem(
                            id=session_id,
                            title=str(data.get("title") or "Đoạn chat mới"),
                            timestamp=str(data.get("timestamp") or ""),
                            message_count=len(messages),
                            last_message=last_msg,
                        )
                    )
                except Exception:
                    continue

    sessions.sort(key=lambda s: s.timestamp, reverse=True)
    return ChatSessionsResponse(sessions=sessions)


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
def delete_chat_session(
    session_id: str,
    request: Request,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> DeleteSessionResponse:
    """Delete a conversation session file with strict user isolation checks."""
    is_web = (request.headers.get("X-Web-Client") == "editorial-monochrome")
    username = current_user.get("username", "guest") if current_user else "guest"
    _check_session_ownership(username, session_id, is_web_client=is_web)

    target_paths = [
        CHAT_HISTORY_DIR / f"{username}_{session_id}.json",
    ]
    if username == "guest" or is_web:
        target_paths.append(CHAT_HISTORY_DIR / f"{session_id}.json")
        for f in CHAT_HISTORY_DIR.glob(f"*{session_id}*.json"):
            if f not in target_paths:
                target_paths.append(f)

    deleted = False
    with _chat_lock:
        for path in target_paths:
            if path.exists():
                try:
                    path.unlink()
                    deleted = True
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Không thể xóa tệp phiên: {str(e)}",
                    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên hội thoại không tồn tại hoặc đã được xóa trước đó.",
        )
    return DeleteSessionResponse(status="deleted", session_id=session_id)
