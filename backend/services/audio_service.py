from __future__ import annotations

import io
import logging
import re
from typing import Any, Dict

from gtts import gTTS
from google.genai import types

from rag_engine import get_gemini_client, GENERATION_MODEL

LOGGER = logging.getLogger(__name__)

MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".webm", ".ogg", ".flac"}
MIME_MAP = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def clean_markdown_for_speech(text: str) -> str:
    """
    Remove markdown formatting, code blocks, URLs, and table artifacts
    so text sounds natural when converted to speech.
    """
    if not text:
        return ""

    # Replace code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " [đoạn mã đã lược bỏ] ", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Replace URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)

    # Process markdown tables: convert lines like '| Tiêu chí | Sách 1 |' into readable text
    lines = []
    for line in cleaned.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("|") and trimmed.endswith("|"):
            # Skip separator lines like |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", trimmed):
                continue
            # Extract cells
            cells = [c.strip() for c in trimmed.strip("|").split("|") if c.strip()]
            if cells:
                lines.append(": ".join(cells) + ".")
        else:
            lines.append(line)
    cleaned = "\n".join(lines)

    # Remove headers: # Header -> Header
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)

    # Remove bold/italic: **text** -> text, *text* -> text
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

    # Remove blockquotes and list bullets
    cleaned = re.sub(r"^\s*>\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # Remove horizontal rules
    cleaned = re.sub(r"^-{3,}$", "", cleaned, flags=re.MULTILINE)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Limit maximum length to ~2500 characters for snappy TTS responses
    if len(cleaned) > 2500:
        cleaned = cleaned[:2450] + "... và một số thông tin khác có trong câu trả lời."

    return cleaned


def generate_tts_audio_bytes(text: str, lang: str = "vi") -> bytes:
    """
    Convert text to speech MP3 bytes using gTTS.
    Returns MP3 bytes.
    """
    clean_text = clean_markdown_for_speech(text)
    if not clean_text:
        clean_text = "Nội dung câu trả lời rỗng."

    fp = io.BytesIO()
    try:
        tts = gTTS(text=clean_text, lang=lang or "vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.getvalue()
    except Exception as e:
        LOGGER.exception("gTTS generation failed: %s", e)
        raise RuntimeError(f"Không thể tạo âm thanh: {str(e)}") from e


def transcribe_audio_bytes(filename: str, audio_bytes: bytes, declared_mime: str | None = None) -> Dict[str, Any]:
    """
    Transcribe recorded audio to Vietnamese text using Gemini Multimodal Audio.
    """
    if not audio_bytes:
        return {"success": False, "text": "", "message": "Tệp âm thanh rỗng."}

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        return {
            "success": False,
            "text": "",
            "message": f"Dung lượng âm thanh vượt quá giới hạn ({MAX_AUDIO_SIZE // (1024 * 1024)} MB).",
        }

    # Detect MIME type
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    
    mime_type = declared_mime or MIME_MAP.get(ext, "audio/wav")
    if mime_type not in MIME_MAP.values() and ext not in ALLOWED_AUDIO_EXTENSIONS:
        # Fallback to audio/wav or audio/mp4 if unknown
        mime_type = "audio/wav"

    try:
        client = get_gemini_client()
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        prompt = (
            "Bạn là trợ lý nhận diện giọng nói tiếng Việt chuyên nghiệp của thư viện sách điện tử.\n"
            "Hãy nghe đoạn âm thanh này và chuyển đổi thành văn bản tiếng Việt chính xác nhất.\n"
            "Chỉ trả về duy nhất đoạn văn bản đã nhận diện được bằng tiếng Việt chuẩn có dấu.\n"
            "Tuyệt đối KHÔNG thêm bất kỳ lời chào, giải thích, bình luận, trích dẫn hay dấu ngoặc kép nào.\n"
            "Nếu đoạn âm thanh chỉ có tạp âm, im lặng hoặc không có giọng nói con người, chỉ trả về chuỗi rỗng: EMPTY_SPEECH"
        )

        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[audio_part, prompt],
        )

        result_text = (response.text or "").strip()
        LOGGER.info("STT raw output: %s", result_text)

        if not result_text or result_text == "EMPTY_SPEECH" or "không có giọng nói" in result_text.lower():
            return {
                "success": False,
                "text": "",
                "message": "Không nhận diện được giọng nói rõ ràng. Vui lòng nói lại.",
            }

        # Clean any surrounding quotes
        cleaned_transcript = result_text.strip('"`\'')

        return {
            "success": True,
            "text": cleaned_transcript,
            "message": "Nhận diện giọng nói thành công.",
        }

    except Exception as e:
        LOGGER.exception("Audio transcription failed: %s", e)
        return {
            "success": False,
            "text": "",
            "message": f"Lỗi nhận diện âm thanh: {str(e)}",
        }
