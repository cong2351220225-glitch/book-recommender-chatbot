from __future__ import annotations

import re

from rag_engine import (
    BOOK_QUERY,
    BOOK_RECOMMENDATION_NEEDS_CONTEXT,
    LIBRARY_INFO,
    OUT_OF_DOMAIN,
    SMALL_TALK,
    classify_query,
    _normalize_query,
)

SMALL_TALK = SMALL_TALK
BOOK_SEARCH = "book_search"
BOOK_RECOMMENDATION = "book_recommendation"
BOOK_DETAIL = "book_detail"
BOOK_COMPARISON = "book_comparison"
AUTHOR_SEARCH = "author_search"
AUTHOR_DETAIL = "author_detail"
GENRE_SEARCH = "genre_search"
LIBRARY_INFO = LIBRARY_INFO
LIBRARY_SEARCH = "library_search"
LOCATION_BOOKSTORE = "location_bookstore"
LOCATION_LIBRARY = "location_library"
LOCATION_SEARCH = "location_search"
FIND_BOOKSTORE = LOCATION_BOOKSTORE
FIND_LIBRARY = LOCATION_LIBRARY
SET_LOCATION = "set_location"
LOCATION_HELP = "location_help"
READ_BOOK = "read_book"
GENERAL_QUESTION = "general_question"
GENERAL = GENERAL_QUESTION
RECOMMENDATION_INTERVIEW = "recommendation_interview"
UNKNOWN = "unknown"


def normalize_user_location(location: str) -> str:
    """Normalize common user-entered city names without using device GPS."""
    value = " ".join(str(location or "").strip().split())
    aliases = {
        "da nang": "Đà Nẵng",
        "đà nẵng": "Đà Nẵng",
        "hue": "Huế",
        "huế": "Huế",
        "ha noi": "Hà Nội",
        "hà nội": "Hà Nội",
        "ho chi minh": "TP Hồ Chí Minh",
        "tp ho chi minh": "TP Hồ Chí Minh",
        "tphcm": "TP Hồ Chí Minh",
        "can tho": "Cần Thơ",
        "cần thơ": "Cần Thơ",
    }
    return aliases.get(value.casefold(), value)


def extract_user_location(question: str) -> str:
    """Extract only a place the user explicitly typed, never precise device GPS."""
    text = str(question or "").strip()
    patterns = (
        r"\b(?:tôi|toi|mình|minh)\s+(?:đang\s+)?(?:ở|o|tại|tai)\s+([^,.;!?]+)",
        r"\b(?:tại|tai)\s+([^,.;!?]+)",
        r"\b(?:ở|o)\s+([^,.;!?]+)",
        r"\b(?:khu\s+vực|khu\s+vuc)\s+([^,.;!?]+)",
        r"\b(?:gần|gan)\s+([^,.;!?]+)",
    )
    stop_words = {
        "đây", "day", "tôi", "toi", "mình", "minh", "gần đây", "gan day",
        "gần tôi", "gan toi", "nào", "nao", "không", "khong", "nhất", "nhat",
        "nhà sách", "nha sach", "thư viện", "thu vien", "sách", "sach", "đó", "do",
        "cuốn sách", "cuon sach", "bán", "ban", "mua", "nơi", "noi"
    }
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            cleaned = re.sub(
                r"\s+(?:không|khong|ko|k|nào|nao|vậy|vay|nhỉ|nhi)\s*$",
                "",
                raw,
                flags=re.IGNORECASE,
            ).strip()
            if cleaned and cleaned.lower() not in stop_words:
                return normalize_user_location(cleaned)
    known_places = [
        "Đà Nẵng", "Huế", "Hà Nội", "TP Hồ Chí Minh", "TP.HCM", "Cần Thơ",
        "Hải Phòng", "Nha Trang", "Vũng Tàu", "Bình Dương", "Đà Lạt"
    ]
    for place in known_places:
        if re.search(rf"\b{re.escape(place)}\b", text, flags=re.IGNORECASE):
            return normalize_user_location(place)
    return ""


def classify_intent(question: str, conversation_history: list[dict] | None = None) -> str:
    normalized = _normalize_query(question)
    if not question or not question.strip():
        return UNKNOWN

    # Ưu tiên nhận diện LIBRARY_INFO nếu câu hỏi về số lượng sách, tác giả, thể loại trong thư viện số
    library_stat_terms = (
        "bao nhieu sach", "co bao nhieu", "bao nhieu cuon", "bao nhieu dau sach",
        "the loai nao", "tac gia nao", "kho du lieu", "kho thu vien",
        "thu vien hien co", "du lieu sach", "the loai nao nhieu nhat", "thong ke"
    )
    if any(term in normalized for term in library_stat_terms):
        return LIBRARY_INFO

    bookstore_location_terms = (
        "nha sach", "hieu sach", "bookstore", "noi ban", "tim noi ban",
        "dia chi ban", "dia chi mua", "mua o dau", "ban o dau", "dia chi nha sach",
        "mua sach o dau", "ban sach o dau", "mua sach", "ban sach", "tim nha sach",
        "tim hieu sach", "nha sach gan day", "hieu sach gan day", "nha sach o dau"
    )
    library_location_terms = (
        "thu vien", "library", "phong doc", "muon sach o dau", "muon sach",
        "tim thu vien", "dia chi thu vien", "thu vien o dau", "thu vien gan day",
        "thu vien gan toi", "thu vien nao"
    )

    if any(term in normalized for term in bookstore_location_terms):
        return FIND_BOOKSTORE

    if any(term in normalized for term in library_location_terms):
        return FIND_LIBRARY

    if extract_user_location(question):
        return SET_LOCATION
    if len(normalized.split()) <= 5 and any(
        place in normalized
        for place in ("da nang", "hue", "ha noi", "ho chi minh", "tphcm", "tp hcm", "can tho")
    ):
        return SET_LOCATION
    if any(term in normalized for term in ("gan toi", "gan day", "khu vuc nao", "o dau")):
        return LOCATION_HELP

    greeting_terms = ("xin chao", "chao ban", "hello", "hi", "halo", "xin loi", "alo", "a lo")
    if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in greeting_terms):
        return SMALL_TALK
    if normalized in {"toi buon", "minh buon", "toi dang buon", "hom nay toi met", "hom nay met qua", "toi chan", "toi hoi chan"}:
        return SMALL_TALK
    if any(term in normalized for term in ("toi muon tim sach phu hop voi toi", "tim sach phu hop voi toi", "tim mot cuon sach phu hop", "tim sach cho toi", "tim giup toi mot cuon sach")):
        return BOOK_RECOMMENDATION_NEEDS_CONTEXT
    if any(term in normalized for term in ("so sanh", "so sánh")):
        return BOOK_COMPARISON
    if any(term in normalized for term in ("chi tiet", "ve cuon", "ve sach", "noi ve", "book detail", "sach nay noi ve gi", "atomic habits noi ve gi")):
        return BOOK_DETAIL
    if any(term in normalized for term in ("tac gia", "ai viet", "tac pham cua", "sach cua")):
        return AUTHOR_DETAIL if any(term in normalized for term in ("ai viet", "tac pham cua", "sach cua")) else AUTHOR_SEARCH
    if any(term in normalized for term in ("the loai", "the loai nao", "thu vien co nhung the loai nao", "co nhung the loai")):
        return GENRE_SEARCH
    if any(term in normalized for term in ("doc sach", "muon doc", "mo sach", "doc online", "read book")):
        return READ_BOOK
    if any(term in normalized for term in ("tim thu vien gan", "thu vien gan toi", "thu vien gan day", "tim thu vien", "co thu vien nao gan")):
        return FIND_LIBRARY
    if any(term in normalized for term in ("tim nha sach gan", "nha sach gan toi", "tim nha sach", "nha sach gan day", "tim dia chi mua sach", "dia chi mua sach", "mua sach o dau", "noi mua")):
        return FIND_BOOKSTORE
    if any(term in normalized for term in ("tim dia diem", "dia diem doc sach", "tim noi mua", "tim dia chi")):
        return LOCATION_SEARCH
    if any(term in normalized for term in ("tim sach", "tim cuon sach", "tim quyen", "tim sach ve", "toi muon tim sach", "tim tac gia", "tieu de")):
        return BOOK_SEARCH
    if any(term in normalized for term in ("bao nhieu sach", "co bao nhieu", "the loai nao", "tac gia nao")):
        return LIBRARY_INFO
    intent = classify_query(question, conversation_history)
    if intent in {SMALL_TALK, BOOK_QUERY, BOOK_RECOMMENDATION_NEEDS_CONTEXT, LIBRARY_INFO, OUT_OF_DOMAIN}:
        return GENERAL if intent == OUT_OF_DOMAIN else intent
    return GENERAL_QUESTION if question.strip() else UNKNOWN
