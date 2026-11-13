from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Depends, status
from pydantic import BaseModel

from backend.core.security import get_current_user_optional
from backend.services.book_cover_vision_service import recognize_book_cover_from_bytes

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["Book Vision"])


class BookCoverRecognitionResponse(BaseModel):
    success: bool
    is_book_cover: bool
    title: Optional[str] = None
    author: Optional[str] = None
    confidence: float = 0.0
    message: str


@router.post(
    "/books/recognize-cover",
    response_model=BookCoverRecognitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Nhận diện tên sách và tác giả từ ảnh bìa (AI Vision)",
)
async def recognize_cover(
    file: UploadFile = File(..., description="Tệp ảnh bìa (JPG, JPEG, PNG <= 8MB)"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Nhận diện sách qua ảnh bìa bằng Google Gemini Vision:
    1. Kiểm tra tính hợp lệ của tệp ảnh (JPG/PNG, magic bytes, <= 8MB).
    2. Đọc ảnh và gửi đến mô hình Gemini Vision.
    3. Trích xuất tên sách, tác giả và độ tin cậy.
    4. Trả kết quả chuẩn JSON cho client tìm kiếm trong thư viện.
    """
    filename = file.filename or "unknown.jpg"
    declared_mime = file.content_type

    try:
        content = await file.read()
    except Exception as e:
        LOGGER.error("Failed to read uploaded file: %s", e)
        return BookCoverRecognitionResponse(
            success=False,
            is_book_cover=False,
            title=None,
            author=None,
            confidence=0.0,
            message="Không thể đọc nội dung tệp tải lên.",
        )

    result = recognize_book_cover_from_bytes(filename, content, declared_mime)
    return BookCoverRecognitionResponse(**result)
