import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend.services.audio_service import clean_markdown_for_speech

client = TestClient(app)


def test_clean_markdown_for_speech():
    raw_md = (
        "# Tiêu đề lớn\n"
        "Đây là **sách hay** và *đáng đọc*.\n"
        "Xem thêm tại https://example.com/books\n"
        "```python\nprint('code')\n```\n"
        "| Tiêu chí | Atomic Habits | 7 Thói Quen |\n"
        "|---|---|---|\n"
        "| Thể loại | Kỹ năng | Kỹ năng |\n"
        "| Tác giả | James Clear | Stephen Covey |\n"
        "> Lời khuyên cuối cùng: Hãy đọc cả hai cuốn."
    )
    cleaned = clean_markdown_for_speech(raw_md)
    assert "#" not in cleaned
    assert "**" not in cleaned
    assert "https://" not in cleaned
    assert "```" not in cleaned
    assert "|" not in cleaned
    assert "Tiêu đề lớn" in cleaned
    assert "sách hay" in cleaned
    assert "Atomic Habits" in cleaned
    assert "Lời khuyên cuối cùng" in cleaned


def test_tts_endpoint_success():
    resp = client.post(
        "/api/v1/chat/tts",
        json={"text": "Xin chào! Thư viện hiện có 208 đầu sách sẵn sàng phục vụ bạn.", "lang": "vi"},
    )
    assert resp.status_code == 200
    assert "audio/mpeg" in resp.headers.get("content-type", "")
    assert len(resp.content) > 1000


def test_tts_endpoint_empty_text():
    resp = client.post(
        "/api/v1/chat/tts",
        json={"text": "   ", "lang": "vi"},
    )
    assert resp.status_code == 400


def test_vision_endpoint_invalid_file():
    fake_file = io.BytesIO(b"This is not a real image file content")
    resp = client.post(
        "/api/v1/books/recognize-cover",
        files={"file": ("fake_image.txt", fake_file, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["is_book_cover"] is False
    assert "không hợp lệ" in data["message"].lower() or "định dạng" in data["message"].lower()


def test_vision_endpoint_oversized():
    # 9 MB dummy payload
    oversized = io.BytesIO(b"0" * (9 * 1024 * 1024))
    resp = client.post(
        "/api/v1/books/recognize-cover",
        files={"file": ("huge_image.jpg", oversized, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "vượt quá giới hạn" in data["message"]


def test_stt_endpoint_empty_file():
    empty_file = io.BytesIO(b"")
    resp = client.post(
        "/api/v1/chat/transcribe-audio",
        files={"file": ("empty.wav", empty_file, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "rỗng" in data["message"]
