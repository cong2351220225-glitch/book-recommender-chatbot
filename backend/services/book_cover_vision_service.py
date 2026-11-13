from __future__ import annotations

import io
import json
import logging
import re
from typing import Any, Dict

from PIL import Image
from google.genai import types

from rag_engine import get_gemini_client, GENERATION_MODEL

LOGGER = logging.getLogger(__name__)

MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class VisionServiceError(Exception):
    """Custom exception for vision service failures."""
    pass


def validate_image_file(filename: str, file_bytes: bytes, declared_mime: str | None = None) -> str:
    """
    Validate that uploaded file is a valid JPG/PNG image and within size limits.
    Returns the verified MIME type.
    """
    if not file_bytes:
        raise VisionServiceError("Tập tin tải lên rỗng.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise VisionServiceError(f"Dung lượng ảnh vượt quá giới hạn cho phép ({MAX_FILE_SIZE // (1024 * 1024)} MB).")

    # Check extension
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise VisionServiceError(f"Định dạng tệp không được hỗ trợ ({ext}). Vui lòng chọn ảnh JPG hoặc PNG.")

    # Validate image magic bytes using Pillow
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.verify()
            fmt = (img.format or "").upper()
            if fmt not in {"JPEG", "PNG"}:
                raise VisionServiceError(f"Định dạng ảnh thực tế ({fmt}) không hợp lệ. Chỉ chấp nhận JPG/PNG.")
    except Exception as e:
        if isinstance(e, VisionServiceError):
            raise
        LOGGER.warning("Image verification failed: %s", e)
        raise VisionServiceError("Nội dung tệp bị hỏng hoặc không phải là hình ảnh hợp lệ.")

    # Determine real MIME
    if fmt == "PNG":
        return "image/png"
    return "image/jpeg"


def recognize_book_cover_from_bytes(filename: str, file_bytes: bytes, declared_mime: str | None = None) -> Dict[str, Any]:
    """
    Recognize a book cover using Gemini Vision model.
    Returns a dictionary with success, is_book_cover, title, author, confidence, message.
    """
    try:
        verified_mime = validate_image_file(filename, file_bytes, declared_mime)
    except VisionServiceError as e:
        return {
            "success": False,
            "is_book_cover": False,
            "title": None,
            "author": None,
            "confidence": 0.0,
            "message": str(e),
        }

    try:
        client = get_gemini_client()
        image_part = types.Part.from_bytes(data=file_bytes, mime_type=verified_mime)

        prompt = (
            "Bạn là thủ thư chuyên nghiệp và chuyên gia nhận diện sách qua ảnh bìa.\n"
            "Hãy quan sát kỹ bức ảnh này và phân tích xem đây có phải là ảnh bìa một cuốn sách hay không.\n"
            "Nếu là bìa sách, hãy đọc chính xác tên cuốn sách và tên tác giả (nếu nhìn thấy trên bìa).\n"
            "Tuyệt đối không bịa đặt hoặc tự đoán khi chữ trên ảnh không đủ rõ.\n"
            "Trả về DUY NHẤT một chuỗi JSON hợp lệ (không kèm markdown ```json hay giải thích nào khác) theo mẫu sau:\n"
            "{\n"
            '  "is_book_cover": true,\n'
            '  "title": "Tên sách chính xác",\n'
            '  "author": "Tên tác giả nếu có hoặc null",\n'
            '  "confidence": 0.95,\n'
            '  "message": "Nhận diện thành công"\n'
            "}\n"
            "Nếu bức ảnh không phải bìa sách, ảnh phong cảnh, ảnh người, ảnh mờ hoặc không đọc được chữ, hãy trả về:\n"
            "{\n"
            '  "is_book_cover": false,\n'
            '  "title": null,\n'
            '  "author": null,\n'
            '  "confidence": 0.0,\n'
            '  "message": "Không nhận diện được bìa sách hoặc chữ trên ảnh quá mờ"\n'
            "}"
        )

        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[image_part, prompt],
        )

        raw_text = (response.text or "").strip()
        LOGGER.info("Gemini Vision response: %s", raw_text)

        # Parse JSON from response
        # Strip code fences if present
        clean_json = raw_text
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.IGNORECASE)
            clean_json = re.sub(r"\s*```$", "", clean_json)

        # Extract first JSON object
        json_match = re.search(r"\{.*\}", clean_json, flags=re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            is_cover = bool(data.get("is_book_cover", False))
            title = data.get("title")
            author = data.get("author")
            confidence = float(data.get("confidence", 0.0))
            msg = data.get("message") or ("Nhận diện thành công" if is_cover else "Không phải bìa sách")

            if is_cover and title:
                return {
                    "success": True,
                    "is_book_cover": True,
                    "title": str(title).strip(),
                    "author": str(author).strip() if author else None,
                    "confidence": round(confidence, 2) if confidence > 0 else 0.9,
                    "message": msg,
                }
            else:
                return {
                    "success": False,
                    "is_book_cover": False,
                    "title": None,
                    "author": None,
                    "confidence": 0.0,
                    "message": msg or "Không nhận diện được tên sách từ ảnh.",
                }
        else:
            return {
                "success": False,
                "is_book_cover": False,
                "title": None,
                "author": None,
                "confidence": 0.0,
                "message": "Phản hồi từ AI không đúng định dạng.",
            }

    except Exception as e:
        LOGGER.exception("Error during book cover recognition: %s", e)
        return {
            "success": False,
            "is_book_cover": False,
            "title": None,
            "author": None,
            "confidence": 0.0,
            "message": f"Lỗi trong quá trình nhận diện: {str(e)}",
        }
