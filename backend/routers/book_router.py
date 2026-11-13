from __future__ import annotations

import logging
import math
import re
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Body, status
from google.genai import types

LOGGER = logging.getLogger(__name__)

from backend.core.config import CHROMA_PATH, COLLECTION_NAME
from backend.core.database import get_books_df
from backend.schemas.book_schema import (
    BookOut,
    BookListResponse,
    BookDetailResponse,
    BookSummaryRequest,
    BookSummaryResponse,
    BookQARequest,
    BookQAResponse,
)
from book_service import search_books, get_book_by_id, get_related_books
from reading_service import (
    can_read,
    reading_status,
    extract_reading_text,
    get_book_specific_reading_file,
)
from rag_engine import get_gemini_client, GENERATION_MODEL

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("/languages", response_model=list[str])
def list_languages() -> list[str]:
    """Get distinct languages present in the library dataset."""
    books_df = get_books_df()
    if books_df.empty or "language" not in books_df.columns:
        return []
    raw_langs = books_df["language"].dropna().astype(str).unique().tolist()
    valid_langs = sorted([l.strip() for l in raw_langs if l.strip()])
    return valid_langs


@router.get("", response_model=BookListResponse)
def list_books(
    q: str | None = Query(None, description="Search keyword across title, author, ISBN, summary, tags"),
    title: str | None = Query(None, description="Filter specifically by book title"),
    author: str | None = Query(None, description="Filter specifically by author name"),
    isbn: str | None = Query(None, description="Filter specifically by ISBN"),
    genre: str | None = Query(None, description="Filter by genre"),
    language: str | None = Query(None, description="Filter by language"),
    min_year: int | None = Query(None, description="Minimum publication year"),
    max_year: int | None = Query(None, description="Maximum publication year"),
    min_rating: float | None = Query(None, description="Minimum rating 0.0 to 5.0"),
    featured_only: bool = Query(False, description="Filter featured books only"),
    reading_only: bool = Query(False, description="Filter books with online reading available"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("Phù hợp", description="Sort order: Phù hợp, Tên A-Z, Tên Z-A, Năm mới nhất, Năm cũ nhất, Đánh giá cao, Đánh giá thấp"),
) -> BookListResponse:
    books_df = get_books_df()
    if books_df.empty:
        return BookListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    filtered_df = books_df.copy()

    # ISBN specific filter
    if isbn and isbn.strip():
        clean_target = "".join(ch for ch in isbn if ch.isdigit() or ch.upper() == "X")
        if clean_target:
            mask = filtered_df["isbn"].astype(str).apply(
                lambda val: clean_target in "".join(ch for ch in val if ch.isdigit() or ch.upper() == "X")
            )
            filtered_df = filtered_df[mask]

    # Title specific filter
    if title and title.strip():
        t_val = title.strip().lower()
        filtered_df = filtered_df[
            filtered_df["title"].astype(str).str.lower().str.contains(t_val, regex=False, na=False)
        ]

    # Author specific filter
    if author and author.strip() and author.strip() != "Tất cả":
        a_val = author.strip().lower()
        filtered_df = filtered_df[
            filtered_df["author"].astype(str).str.lower().str.contains(a_val, regex=False, na=False)
            | filtered_df["author_id"].astype(str).str.lower().str.contains(a_val, regex=False, na=False)
        ]

    # Reading availability filter
    if reading_only:
        filtered_df = filtered_df[
            filtered_df["reading_available"].astype(str).str.lower().isin(["true", "1"])
        ]

    # General query and standard filters using book_service.search_books
    query_str = q.strip() if q else ""
    genre_str = genre.strip() if genre else "Tất cả"
    lang_str = language.strip() if language else "Tất cả"

    year_range = None
    if min_year is not None or max_year is not None:
        start_y = min_year if min_year is not None else int(books_df["year"].min())
        end_y = max_year if max_year is not None else int(books_df["year"].max())
        year_range = (start_y, end_y)

    result_df = search_books(
        books=filtered_df,
        query=query_str,
        genre=genre_str,
        language=lang_str,
        year_range=year_range,
        min_rating=min_rating or 0.0,
        featured_only=featured_only,
        sort_by=sort_by,
    )

    total = len(result_df)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = result_df.iloc[start_idx:end_idx].to_dict(orient="records")

    items = [BookOut(**rec) for rec in page_records]
    return BookListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{book_id}", response_model=BookDetailResponse)
def get_book_detail(book_id: str) -> BookDetailResponse:
    books_df = get_books_df()
    book_rec = get_book_by_id(book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{book_id}' not found",
        )

    # Related books
    related_df = get_related_books(books_df, book_rec, limit=5)
    related_list = [BookOut(**r) for r in related_df.to_dict(orient="records")] if not related_df.empty else []

    can_read_val = can_read(book_rec)
    status_val = reading_status(book_rec)

    return BookDetailResponse(
        book=BookOut(**book_rec),
        related_books=related_list,
        reading_status=status_val,
        can_read=can_read_val,
    )


@router.get("/{book_id}/related", response_model=list[BookOut])
def get_book_related(book_id: str, limit: int = Query(5, ge=1, le=20)) -> list[BookOut]:
    books_df = get_books_df()
    book_rec = get_book_by_id(book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{book_id}' not found",
        )
    related_df = get_related_books(books_df, book_rec, limit=limit)
    if related_df.empty:
        return []
    return [BookOut(**r) for r in related_df.to_dict(orient="records")]


@router.post("/{book_id}/summary", response_model=BookSummaryResponse)
def summarize_book(
    book_id: str,
    req: BookSummaryRequest = Body(...),
) -> BookSummaryResponse:
    """
    AI Book Summarization:
    - If valid full-text electronic document is available, summarizes actual content.
    - If full-text is not available, summarizes based on verified library metadata with clear disclaimer.
    """
    books_df = get_books_df()
    book_rec = get_book_by_id(book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuốn sách với mã '{book_id}'",
        )

    title = str(book_rec.get("title", ""))
    author = str(book_rec.get("author", ""))
    summary_type_str = "ngắn gọn, súc tích" if req.summary_type == "short" else "chi tiết và chuyên sâu"

    has_full_text = get_book_specific_reading_file(book_rec) is not None
    extracted_text = extract_reading_text(book_rec, max_chars=8000, specific_only=True) if has_full_text else ""

    client = get_gemini_client()

    if has_full_text and extracted_text:
        source_type = "full_text"
        notice = "Bản tóm tắt được trích xuất và tổng hợp trực tiếp từ toàn văn tài liệu đọc số của cuốn sách trong thư viện."
        prompt = (
            f"Bạn là thủ thư AI chuyên nghiệp của Thư viện số.\n"
            f"Hãy viết bản tóm tắt {summary_type_str} nội dung cuốn sách '{title}' của tác giả '{author}' "
            f"dựa TRỰC TIẾP trên TOÀN VĂN TÀI LIỆU được cung cấp dưới đây:\n\n"
            f"--- TOÀN VĂN TÀI LIỆU ĐỌC CỦA SÁCH ---\n"
            f"{extracted_text}\n"
            f"--- HẾT TÀI LIỆU ---\n\n"
            f"YÊU CẦU:\n"
            f"1. Chỉ tóm tắt những nội dung, tư tưởng hoặc bài học có trong tài liệu trên.\n"
            f"2. Không tự suy diễn hay bịa đặt thông tin không có trong tài liệu.\n"
            f"3. Trình bày bằng tiếng Việt mạch lạc, chuyên nghiệp."
        )
    else:
        source_type = "metadata"
        notice = "Sách này hiện chưa có bản đọc toàn văn trong thư viện số. Bản tóm tắt được tổng hợp từ thông tin mô tả và siêu dữ liệu chính thức."
        meta_genre = book_rec.get("genre", "")
        meta_year = book_rec.get("year", "")
        meta_desc = book_rec.get("description", "")
        meta_summary = book_rec.get("summary", "")
        meta_target = book_rec.get("target_audience", "")
        meta_tags = book_rec.get("tags", "")

        prompt = (
            f"Bạn là thủ thư AI chuyên nghiệp của Thư viện số.\n"
            f"Cuốn sách '{title}' của tác giả '{author}' hiện CHƯA có bản toàn văn điện tử trong thư viện.\n"
            f"Dưới đây là thông tin giới thiệu chính thức từ thư viện:\n"
            f"- Thể loại: {meta_genre}\n"
            f"- Năm xuất bản: {meta_year}\n"
            f"- Mô tả nội dung: {meta_desc}\n"
            f"- Tóm lược: {meta_summary}\n"
            f"- Đối tượng độc giả: {meta_target}\n"
            f"- Chủ đề/Từ khóa: {meta_tags}\n\n"
            f"YÊU CẦU:\n"
            f"Hãy viết một bản tóm lược giới thiệu ({summary_type_str}) cuốn sách này cho bạn đọc. "
            f"Ghi chú rõ ràng rằng phần tóm lược này được tổng hợp từ thông tin giới thiệu và siêu dữ liệu chính thức "
            f"do sách chưa có bản đọc toàn văn trong thư viện."
        )

    try:
        resp = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1000,
            ),
        )
        summary_result = resp.text.strip() if resp and resp.text else ""
    except Exception as exc:
        # Graceful fallback when Gemini API limit/error occurs
        if has_full_text and extracted_text:
            first_lines = [l.strip() for l in extracted_text.split("\n") if l.strip()][:4]
            snippet = " ".join(first_lines)
            summary_result = (
                f"Cuốn sách '{title}' của tác giả {author}. "
                f"Tài liệu đọc ghi nhận nội dung: {snippet} "
                f"(Tóm lược tự động từ tài liệu đọc số trong thư viện)."
            )
        else:
            meta_desc = str(book_rec.get("description", "")).strip() or str(book_rec.get("summary", "")).strip()
            summary_result = (
                f"Tác phẩm '{title}' của tác giả {author}, thuộc thể loại {book_rec.get('genre', 'Tổng hợp')}. "
                f"{meta_desc} "
                f"Đối tượng bạn đọc phù hợp: {book_rec.get('target_audience', 'Mọi bạn đọc')}."
            )

    return BookSummaryResponse(
        book_id=book_id,
        title=title,
        author=author,
        source_type=source_type,
        summary=summary_result,
        has_full_text=bool(has_full_text and extracted_text),
        notice=notice,
    )


@router.post("/{book_id}/qa", response_model=BookQAResponse)
def qa_book(
    book_id: str,
    req: BookQARequest = Body(...),
) -> BookQAResponse:
    """
    Isolated Q&A specifically for a selected book:
    - Strictly restricts retrieval context to the specified book_id.
    - Zero context leakage from any other book in the catalog.
    - Disclaims clearly if the question cannot be answered from the book's verified material.
    """
    books_df = get_books_df()
    book_rec = get_book_by_id(book_id, books=books_df)
    if not book_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cuốn sách với mã '{book_id}'",
        )

    title = str(book_rec.get("title", ""))
    author = str(book_rec.get("author", ""))

    # 1. Strictly isolated ChromaDB retrieval for book_id only
    isolated_docs: list[str] = []
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = chroma_client.get_collection(name=COLLECTION_NAME)
        got = col.get(ids=[book_id], include=["documents", "metadatas"])
        if got and got.get("documents") and got["documents"]:
            isolated_docs.append(str(got["documents"][0]))
    except Exception:
        pass

    # 2. Check full-text if available
    has_specific_file = get_book_specific_reading_file(book_rec) is not None
    full_text = extract_reading_text(book_rec, max_chars=8000, specific_only=True) if has_specific_file else ""
    if full_text:
        context_source = "full_text"
        isolated_docs.append(f"TOÀN VĂN ĐIỆN TỬ:\n{full_text}")
    else:
        context_source = "metadata"

    # 3. Assemble book-isolated context
    book_context = (
        f"MÃ SÁCH: {book_id}\n"
        f"TIÊU ĐỀ: {title}\n"
        f"TÁC GIẢ: {author}\n"
        f"THỂ LOẠI: {book_rec.get('genre', '')}\n"
        f"NĂM XUẤT BẢN: {book_rec.get('year', '')}\n"
        f"MÔ TẢ: {book_rec.get('description', '')}\n"
        f"TÓM LƯỢC: {book_rec.get('summary', '')}\n"
        f"ĐỐI TƯỢNG PHÙ HỢP: {book_rec.get('target_audience', '')}\n"
        f"TỪ KHÓA: {book_rec.get('tags', '')}\n"
    )
    if isolated_docs:
        book_context += "\nTÀI LIỆU TRÍCH XUẤT CỦA CUỐN SÁCH:\n" + "\n---\n".join(isolated_docs)

    system_instruction = (
        f"Bạn là trợ lý giải đáp câu hỏi chuyên sâu DUY NHẤT về cuốn sách '{title}' của tác giả '{author}'.\n"
        f"CHỈ ĐƯỢC PHÉP sử dụng thông tin trong NGỮ CẢNH CỦA CUỐN SÁCH ĐƯỢC CUNG CẤP để trả lời.\n"
        f"TUYỆT ĐỐI KHÔNG sử dụng hay liên hệ kiến thức từ bất kỳ cuốn sách nào khác ngoài cuốn sách này.\n"
        f"Nếu câu hỏi của người dùng hỏi về thông tin không có hoặc không thể suy luận chắc chắn từ tài liệu của cuốn sách này, "
        f"bạn BẮT BUỘC phải trả lời rõ ràng: 'Thông tin này không có trong tài liệu của cuốn sách {title}.'\n"
        f"Trả lời bằng tiếng Việt lịch sự, trung thực, chính xác."
    )

    prompt = (
        f"NGỮ CẢNH DUY NHẤT CỦA CUỐN SÁCH:\n"
        f"{book_context}\n\n"
        f"CÂU HỎI CỦA BẠN ĐỌC DÀNH CHO CUỐN SÁCH NÀY:\n"
        f"{req.question.strip()}\n"
    )

    try:
        client = get_gemini_client()
        resp = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                max_output_tokens=1000,
            ),
        )
        answer = resp.text.strip() if resp and resp.text else f"Thông tin này không có trong tài liệu của cuốn sách {title}."
    except Exception as exc:
        # Fallback keyword matching against strictly isolated book context
        LOGGER.warning("Gemini QA failed or unavailable: %s. Using isolated strict context fallback.", exc)
        q_lower = req.question.strip().lower()
        stopwords = {
            "của", "cho", "và", "các", "những", "sách", "này", "trong", "được", "người",
            "cuốn", "thế", "nào", "đâu", "nói", "đến", "chiếc", "có", "là", "gì", "ở",
            "bao", "nhiêu", "viết", "về", "cách", "ra", "sao", "hãy", "biết", "với",
            "tại", "một", "tôi", "bạn", "hỏi", "thử", "xem", "như", "làm", "nhất", "rất",
            "khi", "đó", "thì", "từ", "lại", "đã", "sẽ", "đang", "nội", "dung", "tìm",
            "hiểu", "giúp", "mình", "ai", "bởi", "vì"
        }
        tokens = re.findall(r"\w+", q_lower)
        meaningful_keywords = [w for w in tokens if len(w) >= 2 and w not in stopwords]

        matching_lines: list[str] = []
        if meaningful_keywords:
            lines = [line.strip() for line in book_context.split("\n") if len(line.strip()) > 10]
            scored_lines: list[tuple[int, str]] = []
            for line in lines:
                l_lower = line.lower()
                matched = [kw for kw in meaningful_keywords if kw in l_lower]
                if len(meaningful_keywords) == 1 and len(matched) == 1:
                    scored_lines.append((1, line))
                elif len(matched) >= 2 or (len(meaningful_keywords) >= 2 and (len(matched) / len(meaningful_keywords)) >= 0.5):
                    scored_lines.append((len(matched), line))

            scored_lines.sort(key=lambda x: x[0], reverse=True)
            matching_lines = [line for _, line in scored_lines[:3]]

        if matching_lines:
            answer = (
                f"Dựa trên thông tin của cuốn sách '{title}':\n"
                + "\n".join(f"- {l}" for l in matching_lines)
            )
        else:
            answer = f"Thông tin này không có trong tài liệu của cuốn sách {title}."

    has_context = "không có trong tài liệu" not in answer.lower()

    return BookQAResponse(
        book_id=book_id,
        title=title,
        author=author,
        question=req.question.strip(),
        answer=answer,
        context_source=context_source,
        has_sufficient_context=has_context,
    )


