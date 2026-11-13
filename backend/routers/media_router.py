from __future__ import annotations

import io
import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.security import get_current_user_optional
from backend.services.audio_service import generate_tts_audio_bytes, transcribe_audio_bytes

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["Media & Voice"])


class TTSRequest(BaseModel):
    text: str
    lang: Optional[str] = "vi"


class STTResponse(BaseModel):
    success: bool
    text: str
    message: str


@router.post(
    "/chat/tts",
    status_code=status.HTTP_200_OK,
    summary="Chuyển văn bản câu trả lời thành giọng nói tiếng Việt (TTS)",
)
async def text_to_speech_endpoint(
    request: TTSRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Tạo luồng âm thanh MP3 từ văn bản tiếng Việt bằng gTTS:
    - Loại bỏ định dạng Markdown thô, liên kết và khối bảng.
    - Trả về luồng âm thanh audio/mpeg.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung văn bản để tạo giọng nói không được rỗng.",
        )

    try:
        mp3_bytes = generate_tts_audio_bytes(request.text, lang=request.lang or "vi")
        return StreamingResponse(
            io.BytesIO(mp3_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception as e:
        LOGGER.exception("TTS endpoint failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể chuyển đổi văn bản sang âm thanh: {str(e)}",
        )


@router.post(
    "/chat/transcribe-audio",
    response_model=STTResponse,
    status_code=status.HTTP_200_OK,
    summary="Nhận diện giọng nói tiếng Việt từ micro (Speech-to-Text)",
)
async def transcribe_audio_endpoint(
    file: UploadFile = File(..., description="Tệp ghi âm micro (.wav, .mp3, .m4a, .webm <= 10MB)"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Chuyển đổi bản ghi âm micro thành văn bản tiếng Việt qua Google Gemini Audio:
    1. Tiếp nhận tệp âm thanh từ client Flutter.
    2. Gửi dữ liệu âm thanh đến mô hình AI.
    3. Nhận diện giọng nói tiếng Việt chuẩn xác có dấu.
    4. Trả kết quả văn bản để người dùng xem và chỉnh sửa trước khi gửi.
    """
    filename = file.filename or "recording.wav"
    declared_mime = file.content_type

    try:
        audio_content = await file.read()
    except Exception as e:
        LOGGER.error("Failed to read uploaded audio file: %s", e)
        return STTResponse(
            success=False,
            text="",
            message="Không thể đọc nội dung tệp ghi âm.",
        )

    result = transcribe_audio_bytes(filename, audio_content, declared_mime)
    return STTResponse(**result)
