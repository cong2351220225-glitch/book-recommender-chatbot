from __future__ import annotations

import base64
from datetime import datetime
import html
import io
import json
import logging
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote_plus
import uuid
import textwrap

import google.generativeai as genai
import pandas as pd
import streamlit as st

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import PIL.Image
except ImportError:
    PIL = None

try:
    from streamlit_mic_recorder import speech_to_text
except ImportError:
    speech_to_text = None

from author_service import get_author, load_authors, search_authors
from book_service import (
    get_book,
    get_books_by_author,
    get_featured_books,
    get_related_books,
    load_books,
    purchase_search_url,
    search_books,
)
from intent_router import (
    FIND_BOOKSTORE,
    FIND_LIBRARY,
    LOCATION_HELP,
    LOCATION_SEARCH,
    SET_LOCATION,
    classify_intent,
    extract_user_location,
    normalize_user_location,
)
from location_service import (
    LocationServiceError,
    build_google_maps_search_url,
    search_bookstores,
    search_libraries,
)
from rag_engine import (
    MAX_TOP_K,
    TOP_K_DEFAULT,
    create_reader_profile,
    get_library_book_count,
    handle_user_message,
)
from reading_service import can_read, reading_status, validate_local_file
from crawler_service import (
    BOOK_FIELDS as CRAWLER_BOOK_FIELDS,
    crawl_and_prepare,
    get_unindexed_books,
    ingest_books_to_chroma,
    save_books_to_csv,
    sync_unindexed_books_to_chroma,
)

LOGGER = logging.getLogger(__name__)

# ==========================================
# CẤU HÌNH API KEY AN TOÀN CHO CLOUD
# ==========================================
def get_gemini_api_key() -> str:
    """Lấy API Key từ biến môi trường hoặc Streamlit Cloud Secrets."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key and hasattr(st, "secrets"):
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key or ""

# ==========================================
# CÁC HÀM QUẢN LÝ LỊCH SỬ CHAT (GIỮ NGUYÊN)
# ==========================================
HISTORY_DIR = Path("data/chat_history")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_chat_session(username: str, session_id: str, messages: list) -> None:
    """Lưu đoạn chat hiện tại thành file JSON."""
    if not messages:
        return
    title = (
        messages[0]["content"][:30] + "..."
        if len(messages[0]["content"]) > 30
        else messages[0]["content"]
    )
    file_path = HISTORY_DIR / f"{username}_{session_id}.json"
    data = {
        "id": session_id,
        "title": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_all_chats(username: str) -> list:
    """Đọc danh sách tất cả các đoạn chat của một user."""
    chats = []
    for file_path in HISTORY_DIR.glob(f"{username}_*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                chats.append(data)
        except Exception:
            pass
    return sorted(chats, key=lambda x: x.get("timestamp", ""), reverse=True)


def delete_chat_session(username: str, session_id: str) -> None:
    """Xóa file JSON của một đoạn chat."""
    file_path = HISTORY_DIR / f"{username}_{session_id}.json"
    if file_path.exists():
        file_path.unlink()


# ==========================================
# CÁC HÀM QUẢN LÝ TÀI KHOẢN (GIỮ NGUYÊN)
# ==========================================
USER_DB_FILE = Path("data/users.json")


def load_users() -> dict:
    if not USER_DB_FILE.exists():
        return {}
    with open(USER_DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users: dict) -> None:
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register_user(username: str, password: str) -> bool:
    users = load_users()
    if username in users:
        return False
    users[username] = {"password": password}
    save_users(users)
    return True


def verify_login(username: str, password: str) -> bool:
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True
    return False


# ==========================================
# TEXT-TO-SPEECH (GIỮ NGUYÊN)
# ==========================================
def text_to_speech(text: str) -> bytes | None:
    """Chuyển đổi văn bản thành âm thanh tiếng Việt."""
    try:
        clean_text = re.sub(r"[*#_`\[\]()]", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            return None
        tts = gTTS(text=clean_text[:500], lang="vi")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        LOGGER.error(f"TTS Error: {e}")
        return None


# ==========================================
# STREAMLIT CONFIG (WIDE LAYOUT & METADATA)
# ==========================================
st.set_page_config(
    page_title="AI Digital Library · Thư viện Số & Trợ lý Đa phương thức",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# COVER & AVATAR SVG PLACEHOLDERS (EMERALD & GOLD)
# ==========================================
def get_book_cover_placeholder_uri(title: str, genre: str = "Sách") -> str:
    """Tạo ảnh bìa vector SVG Emerald & Gold cao cấp khi sách không có cover_url."""
    safe_title = html.escape(str(title or "Thư viện AI"))[:40]
    safe_genre = html.escape(str(genre or "Sách số"))[:20]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450">
      <defs>
        <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#0F172A"/>
          <stop offset="50%" stop-color="#064E3B"/>
          <stop offset="100%" stop-color="#0F766E"/>
        </linearGradient>
        <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#F59E0B"/>
          <stop offset="100%" stop-color="#FDE68A"/>
        </linearGradient>
      </defs>
      <rect width="300" height="450" rx="12" fill="url(#bgGrad)"/>
      <rect x="12" y="12" width="276" height="426" rx="8" fill="none" stroke="url(#goldGrad)" stroke-width="1.5" stroke-opacity="0.6"/>
      <rect x="18" y="18" width="264" height="414" rx="6" fill="none" stroke="#CCFBF1" stroke-width="0.75" stroke-opacity="0.25"/>
      <circle cx="150" cy="140" r="48" fill="#047857" stroke="#F59E0B" stroke-width="2"/>
      <text x="150" y="153" font-family="-apple-system, sans-serif" font-size="34" fill="#FDE68A" text-anchor="middle">📖</text>
      <rect x="50" y="215" width="200" height="26" rx="13" fill="#0F172A" fill-opacity="0.85" stroke="#10B981" stroke-width="1"/>
      <text x="150" y="232" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#6EE7B7" text-anchor="middle" letter-spacing="1.2">{safe_genre.upper()}</text>
      <text x="150" y="280" font-family="-apple-system, sans-serif" font-size="16" font-weight="700" fill="#FFFFFF" text-anchor="middle">
        <tspan x="150" dy="0">{safe_title[:22]}</tspan>
        <tspan x="150" dy="22">{safe_title[22:44]}</tspan>
      </text>
      <line x1="80" y1="340" x2="220" y2="340" stroke="#F59E0B" stroke-width="1.2" stroke-opacity="0.6"/>
      <text x="150" y="375" font-family="-apple-system, sans-serif" font-size="11" font-weight="600" fill="#CCFBF1" fill-opacity="0.85" text-anchor="middle" letter-spacing="2">AI DIGITAL LIBRARY</text>
    </svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


def get_author_avatar_placeholder_uri(name: str) -> str:
    """Tạo avatar SVG monogram Emerald & Gold khi tác giả không có photo_url."""
    safe_name = html.escape(str(name or "Tác giả"))
    initials = "".join([part[0] for part in safe_name.split()[:2]]).upper() or "TG"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
      <defs>
        <linearGradient id="avatarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#064E3B"/>
          <stop offset="100%" stop-color="#0D9488"/>
        </linearGradient>
      </defs>
      <circle cx="80" cy="80" r="76" fill="url(#avatarGrad)" stroke="#F59E0B" stroke-width="3"/>
      <circle cx="80" cy="80" r="70" fill="none" stroke="#FDE68A" stroke-width="1" stroke-dasharray="4,4"/>
      <text x="80" y="93" font-family="-apple-system, sans-serif" font-size="34" font-weight="bold" fill="#FDE68A" text-anchor="middle">{initials}</text>
    </svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


# ==========================================
# STYLESHEET "MODERN EMERALD & SLATE LUXURY"
# ==========================================
st.markdown(
    """
    <style>
    /* CSS Variables & Palette */
    :root {
        --teal-primary: #0D9488;
        --teal-dark: #0F766E;
        --teal-deep: #115E59;
        --teal-light: #14B8A6;
        --teal-subtle: #F0FDFA;
        --teal-chip-bg: #CCFBF1;
        --teal-chip-text: #0F766E;

        --slate-dark: #0F172A;
        --slate-mid: #1E293B;
        --slate-light: #F1F5F9;
        --canvas-bg: #F8FAFC;
        --surface-white: #FFFFFF;

        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #64748B;

        --gold: #F59E0B;
        --gold-light: #FDE68A;
        --gold-subtle: #FFFBEB;

        --border-light: #E2E8F0;
        --border-teal: rgba(13, 148, 136, 0.35);

        --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.05);
        --shadow-md: 0 4px 14px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04);
        --shadow-lg: 0 12px 28px -4px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.05);
        --shadow-teal: 0 12px 24px -4px rgba(13, 148, 136, 0.25);

        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-full: 9999px;
    }

    /* Ẩn các thành phần thừa mặc định của Streamlit */
    #MainMenu {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    header {visibility: hidden !important; display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}

    /* Bố cục Canvas Chính */
    .stApp {
        background-color: var(--canvas-bg);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .block-container {
        max-width: 1380px !important;
        padding-top: 1rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* Typography & Tiêu đề Mục */
    h1, h2, h3, h4, h5, h6 {
        color: var(--slate-dark);
        font-weight: 750;
        letter-spacing: -0.015em;
    }
    .lib-section-title {
        color: var(--slate-dark);
        font-size: 1.4rem;
        font-weight: 750;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.8rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--border-light);
    }
    .lib-section-title::before {
        content: "";
        display: inline-block;
        width: 5px;
        height: 1.3rem;
        background: linear-gradient(180deg, var(--teal-primary), var(--teal-dark));
        border-radius: 3px;
    }

    /* Topbar Điều hướng & Tìm kiếm Toàn cục */
    .top-header-bar {
        background: var(--surface-white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        padding: 0.75rem 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: var(--shadow-sm);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Hero Banner Hiện đại */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #064E3B 45%, #0F766E 85%, #0D9488 100%);
        border-radius: var(--radius-lg);
        padding: 2.4rem 2.8rem;
        color: #FFFFFF;
        position: relative;
        overflow: hidden;
        border-bottom: 4px solid var(--gold);
        box-shadow: var(--shadow-lg);
        margin-bottom: 1.6rem;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(245, 158, 11, 0.2);
        border: 1px solid var(--gold-light);
        color: var(--gold-light);
        padding: 0.35rem 0.9rem;
        border-radius: var(--radius-full);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .hero-badge-dot {
        width: 7px;
        height: 7px;
        background-color: var(--gold);
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px var(--gold);
    }
    .hero-title {
        font-size: 2.25rem;
        font-weight: 850;
        color: #FFFFFF;
        margin: 0 0 0.5rem 0;
        line-height: 1.25;
    }
    .hero-title span {
        background: linear-gradient(90deg, #FDE68A 0%, #F59E0B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-desc {
        font-size: 1.02rem;
        color: #CCFBF1;
        margin: 0 0 1.6rem 0;
        max-width: 820px;
        line-height: 1.55;
    }

    /* Thẻ thống kê 4 cột trong Hero */
    .hero-stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-top: 1.2rem;
    }
    .hero-stat-item {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: var(--radius-md);
        padding: 1rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    .hero-stat-item:hover {
        background: rgba(255, 255, 255, 0.18);
        border-color: var(--gold-light);
        transform: translateY(-2px);
    }
    .hero-stat-num {
        font-size: 1.65rem;
        font-weight: 850;
        color: #FFFFFF;
        margin-bottom: 0.15rem;
    }
    .hero-stat-label {
        font-size: 0.8rem;
        color: #E2E8F0;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    /* Thẻ sách (Book Card Container) */
    .book-card-container {
        background: var(--surface-white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s ease, border-color 0.25s ease;
        display: flex;
        flex-direction: column;
        margin-bottom: 1rem;
        position: relative;
    }
    .book-card-container:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-teal);
        border-color: var(--teal-primary);
    }
    .book-cover-wrap {
        width: 100%;
        height: 220px;
        background: var(--slate-dark);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        position: relative;
    }
    .book-cover-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    .book-card-container:hover .book-cover-img {
        transform: scale(1.04);
    }
    .book-badge-featured {
        position: absolute;
        top: 10px;
        right: 10px;
        background: linear-gradient(135deg, #F59E0B, #D97706);
        color: #FFFFFF;
        font-size: 0.72rem;
        font-weight: 750;
        padding: 0.25rem 0.65rem;
        border-radius: var(--radius-full);
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }
    .book-card-body {
        padding: 1rem 1.1rem;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
    }
    .book-genre-chip {
        display: inline-block;
        background: var(--teal-chip-bg);
        color: var(--teal-chip-text);
        font-size: 0.75rem;
        font-weight: 650;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        margin-bottom: 0.45rem;
        width: fit-content;
    }
    .book-card-title {
        color: var(--slate-dark);
        font-size: 1.02rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        line-height: 1.35;
        height: 2.7rem;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .book-card-author {
        color: var(--text-secondary);
        font-size: 0.88rem;
        font-weight: 550;
        margin: 0 0 0.5rem 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .book-card-meta {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }
    .book-card-desc {
        color: var(--text-secondary);
        font-size: 0.84rem;
        line-height: 1.45;
        height: 2.5rem;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin-bottom: 0.8rem;
    }

    /* Thẻ Chi tiết sách */
    .detail-card {
        background: var(--surface-white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-lg);
        padding: 2rem 2.2rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 1.5rem;
    }
    .detail-tag-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.8rem 0 1.2rem 0;
    }
    .detail-tag-item {
        background: var(--teal-chip-bg);
        color: var(--teal-chip-text);
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.3rem 0.8rem;
        border-radius: var(--radius-full);
    }
    .detail-tag-item.gold {
        background: var(--gold-subtle);
        border: 1px solid var(--gold-light);
        color: #92400E;
    }

    /* Sidebar Dark Slate & Teal Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
        border-right: 1px solid rgba(13, 148, 136, 0.25);
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.12) !important;
    }
    [data-testid="stSidebar"] .stCaption p {
        color: #94A3B8 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(13, 148, 136, 0.4) !important;
        border-radius: var(--radius-sm);
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: #0F766E !important;
        border-color: var(--teal-light) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--teal-primary), var(--teal-dark)) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--teal-light), var(--teal-primary)) !important;
    }

    /* Chat Messages - User & Assistant */
    [data-testid="stChatMessage"] {
        border-radius: var(--radius-md) !important;
        margin: 0.8rem 0 !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: var(--shadow-sm);
    }
    /* User Message Bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%) !important;
        border: 1px solid rgba(13, 148, 136, 0.4) !important;
        border-radius: 18px 18px 4px 18px !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] * {
        color: #FFFFFF !important;
    }
    /* Assistant Message Bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: var(--surface-white) !important;
        border: 1px solid var(--border-light) !important;
        border-left: 4px solid var(--teal-primary) !important;
        border-radius: 18px 18px 18px 4px !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] * {
        color: var(--text-primary) !important;
    }
    [data-testid="stChatInput"] {
        border: 1.5px solid var(--teal-primary) !important;
        border-radius: 26px !important;
        box-shadow: var(--shadow-sm);
    }

    /* Tabs Styling Hiện đại */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--slate-light);
        padding: 6px;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-light);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: var(--radius-sm);
        font-weight: 600;
        font-size: 0.92rem;
        color: var(--text-secondary);
        background-color: transparent;
        border: none;
        padding: 0 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--surface-white) !important;
        color: var(--teal-dark) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
    }

    /* Nút bấm chung trên trang chính */
    .stButton button {
        border-radius: var(--radius-sm);
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--teal-primary), var(--teal-dark)) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(13, 148, 136, 0.3) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--teal-light), var(--teal-primary)) !important;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.4) !important;
    }

    /* Category Cards */
    .genre-card {
        background: var(--surface-white);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        padding: 1.2rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .genre-card:hover {
        border-color: var(--teal-primary);
        transform: translateY(-3px);
        box-shadow: var(--shadow-md);
    }

    /* Hộp Empty State */
    .empty-state-box {
        text-align: center;
        padding: 3rem 1.5rem;
        background: var(--surface-white);
        border: 2px dashed var(--border-light);
        border-radius: var(--radius-lg);
        margin: 1.5rem 0;
    }
    .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# DATA LOADING & CACHE (TƯƠNG THÍCH CLOUD)
# ==========================================
@st.cache_data
def load_library_data(books_mtime: float = 0.0, authors_mtime: float = 0.0, genres_mtime: float = 0.0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    books = load_books()
    authors = load_authors()
    genres_path = "data/genres.csv"
    if os.path.exists(genres_path):
        genres = pd.read_csv(genres_path).fillna("")
    else:
        genres = pd.DataFrame(columns=["genre_id", "name", "description"])
    return books, authors, genres


# ==========================================
# SESSION STATE & NAVIGATION
# ==========================================
def init_state() -> None:
    defaults = {
        "page": "Trang chủ",
        "navigation": "Trang chủ",
        "selected_book_id": "",
        "messages": [],
        "reader_profile": create_reader_profile(),
        "pending_question": "",
        "location_query": "",
        "user_location": "",
        "pending_location_kind": "",
        "username": "",
        "logged_in": False,
        "current_session_id": str(uuid.uuid4()),
        "global_search_query": "",
        "global_search_open": False,
        "top_k": TOP_K_DEFAULT,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate(page: str) -> None:
    st.session_state.page = page
    st.session_state.pending_navigation = page


# ==========================================
# COVER IMAGE RENDERER
# ==========================================
def render_cover_image(book: dict[str, Any], height: int = 220, is_large: bool = False) -> str:
    """Trả về HTML hiển thị ảnh bìa chuẩn hoặc placeholder vector chống vỡ ảnh."""
    url = str(book.get("cover_url", "")).strip()
    title = str(book.get("title", "Sách"))
    genre = str(book.get("genre", "Sách"))
    fallback_uri = get_book_cover_placeholder_uri(title, genre)
    badge_html = '<div class="book-badge-featured">⭐ NỔI BẬT</div>' if book.get("featured") and not is_large else ""

    if url:
        img_html = f'<img src="{html.escape(url)}" alt="{html.escape(title)}" class="book-cover-img" onerror="this.onerror=null; this.src=\'{fallback_uri}\';" />'
    else:
        img_html = f'<img src="{fallback_uri}" alt="{html.escape(title)}" class="book-cover-img" />'

    raw_html = f'<div class="book-cover-wrap" style="height:{height}px;">{img_html}{badge_html}</div>'
    return textwrap.dedent(raw_html).strip()


# ==========================================
# RENDER BOOK CARD & GRID
# ==========================================
def render_book_card(book: dict[str, Any], key_prefix: str) -> None:
    """Render một thẻ sách chuẩn Modern Luxury UI."""
    book_id = str(book.get("book_id", ""))
    title = str(book.get("title", "Không rõ"))
    author = str(book.get("author", "Không rõ"))
    genre = str(book.get("genre", "Chung"))
    year = book.get("year", "N/A")
    rating = float(book.get("rating", 4.0))
    summary = str(book.get("summary") or book.get("description", ""))

    cover_html = render_cover_image(book, height=210)
    card_html = textwrap.dedent(
        f"""
        <div class="book-card-container">
        {cover_html}
        <div class="book-card-body">
        <span class="book-genre-chip">{html.escape(genre)}</span>
        <div class="book-card-title" title="{html.escape(title)}">{html.escape(title)}</div>
        <div class="book-card-author">{html.escape(author)}</div>
        <div class="book-card-meta">
        <span>📅 {year}</span>
        <span>⭐ {rating:.1f}</span>
        </div>
        <div class="book-card-desc">{html.escape(summary)}</div>
        </div>
        </div>
        """
    ).strip()

    if hasattr(st, "html"):
        st.html(card_html)
    else:
        st.markdown(card_html, unsafe_allow_html=True)

    if st.button("📖 Xem chi tiết", key=f"btn_det_{key_prefix}_{book_id}", use_container_width=True):
        st.session_state.selected_book_id = book_id
        navigate("Chi tiết sách")
        st.rerun()


def render_book_grid(frame: pd.DataFrame, key_prefix: str = "grid") -> None:
    """Hiển thị lưới sách dạng 3 cột responsive có xử lý empty state."""
    if frame.empty:
        st.markdown(
            """
            <div class="empty-state-box">
                <div class="empty-state-icon">📚</div>
                <h3>Không tìm thấy cuốn sách nào</h3>
                <p style="color:var(--text-secondary); max-width:450px; margin:0 auto 1.2rem auto;">
                    Thư viện hiện chưa có đầu sách phù hợp với bộ lọc hoặc từ khóa tìm kiếm này.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for start in range(0, len(frame), 3):
        cols = st.columns(3)
        for col, (_, row) in zip(cols, frame.iloc[start : start + 3].iterrows()):
            with col:
                render_book_card(row.to_dict(), key_prefix)


# ==========================================
# RETRIEVED BOOKS & LOCATION RENDERERS
# ==========================================
def render_retrieved_books(books: list[dict[str, Any]], key_prefix: str) -> None:
    """Hiển thị nguồn sách grounding được truy xuất từ ChromaDB."""
    if not books:
        return
    with st.expander(f"📚 Nguồn sách trích xuất từ ChromaDB ({len(books)} ấn phẩm)", expanded=False):
        for index, item in enumerate(books):
            meta = item.get("metadata", {})
            title = str(meta.get("title", "Không rõ"))
            author = str(meta.get("author", "Không rõ"))
            genre = str(meta.get("genre", "Không rõ"))
            year = meta.get("year", "N/A")
            distance = item.get("distance", "N/A")
            book_id = str(meta.get("book_id", ""))

            cover_uri = str(meta.get("cover_url", "")).strip() or get_book_cover_placeholder_uri(title, genre)
            cols = st.columns([1, 4, 1.5])
            with cols[0]:
                st.markdown(
                    f'<img src="{cover_uri}" style="width:100%; max-height:85px; object-fit:cover; border-radius:6px; box-shadow:var(--shadow-sm);"/>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(f"**{html.escape(title)}** · *{html.escape(author)}* ({year})")
                st.caption(f"Thể loại: {genre} | Khoảng cách vector: `{distance}`")
            with cols[2]:
                if book_id and st.button("Xem chi tiết", key=f"{key_prefix}_ret_{index}_{book_id}", use_container_width=True):
                    st.session_state.selected_book_id = book_id
                    navigate("Chi tiết sách")
                    st.rerun()
            st.divider()


def handle_location_request(question: str, user_location: str) -> tuple[str, dict[str, Any] | None]:
    """Xử lý truy vấn địa điểm bằng SerpApi / Local Fallback."""
    intent = classify_intent(question)
    location = extract_user_location(question) or str(user_location or "").strip()
    if not location:
        return "Bạn muốn tìm địa điểm ở khu vực nào? Ví dụ: Đà Nẵng, Huế hoặc Hà Nội.", None
    if intent == FIND_LIBRARY:
        results = search_libraries(location)
        return (
            f"Mình đã tìm thấy **{len(results)}** thư viện gần **{location}**.",
            {
                "results": results,
                "url": build_google_maps_search_url("library", location),
                "kind": "library",
                "location": location,
            },
        )
    if intent in {FIND_BOOKSTORE, LOCATION_SEARCH}:
        results = search_bookstores(location)
        return (
            f"Mình đã tìm thấy **{len(results)}** nhà sách gần **{location}**.",
            {
                "results": results,
                "url": build_google_maps_search_url("bookstore", location),
                "kind": "bookstore",
                "location": location,
            },
        )
    return "Bạn muốn tìm nhà sách hay thư viện ở khu vực nào?", None


def process_pending_location(
    question: str, pending_kind: str, current_location: str
) -> tuple[str, str, dict[str, Any] | None]:
    location = normalize_user_location(extract_user_location(question) or question.strip().rstrip("?.!"))
    if not location:
        return "Bạn đang ở khu vực nào? Ví dụ: Đà Nẵng, Huế hoặc Hà Nội.", current_location, None
    if pending_kind not in {"library", "bookstore"}:
        return (
            f"Đã ghi nhận khu vực của bạn là **{location}**. Bạn có thể yêu cầu mình tìm nhà sách hoặc thư viện gần đó.",
            location,
            None,
        )
    search_question = f"tìm {'thư viện' if pending_kind == 'library' else 'nhà sách'} gần tôi"
    answer, result = handle_location_request(search_question, location)
    return answer, location, result


def render_location_results(location_data: dict[str, Any], key_prefix: str) -> None:
    results = location_data.get("results", [])
    if not results:
        return
    points = [
        {"lat": r["latitude"], "lon": r["longitude"]}
        for r in results
        if isinstance(r.get("latitude"), (int, float)) and isinstance(r.get("longitude"), (int, float))
    ]
    if points:
        st.map(pd.DataFrame(points))
    for index, r in enumerate(results):
        with st.container(border=True):
            st.markdown(f"**📍 {html.escape(str(r.get('title', 'Địa điểm chưa rõ')))}**")
            if r.get("address"):
                st.write(f"Địa chỉ: {r['address']}")
            if r.get("rating"):
                st.write(f"⭐ {r['rating']}/5 ({r.get('reviews', 0)} lượt đánh giá)")
            if r.get("open_state") or r.get("hours"):
                st.write(f"🕒 {r.get('open_state') or r.get('hours')}")
            if r.get("phone"):
                st.write(f"☎️ {r['phone']}")
            actions = st.columns(2 if r.get("website") else 1)
            actions[0].link_button(
                "🧭 Chỉ đường",
                r.get("directions_url") or r.get("google_maps_url", location_data.get("url", "")),
                key=f"{key_prefix}_dir_{index}",
                use_container_width=True,
            )
            if r.get("website"):
                actions[1].link_button(
                    "🌐 Website", r["website"], key=f"{key_prefix}_web_{index}", use_container_width=True
                )


# ==========================================
# GLOBAL SEARCH MODAL / SECTION
# ==========================================
def render_global_search_view(books: pd.DataFrame, authors: pd.DataFrame) -> None:
    """Trang kết quả Tìm kiếm toàn cục phân nhóm SÁCH và TÁC GIẢ."""
    query = st.session_state.get("global_search_query", "").strip()
    st.markdown('<div class="lib-section-title">🔍 Kết quả Tìm kiếm Toàn cục</div>', unsafe_allow_html=True)
    st.caption(f"Từ khóa: **{html.escape(query)}** (tra cứu trực tiếp trong dữ liệu)")

    col_btn, _ = st.columns([2, 5])
    with col_btn:
        if st.button("✕ Đóng và quay lại", use_container_width=True):
            st.session_state.global_search_query = ""
            st.session_state.global_search_open = False
            st.rerun()

    if not query:
        st.info("Vui lòng nhập từ khóa tìm kiếm.")
        return

    books_result = search_books(books, query=query)
    authors_result = search_authors(authors, query=query)

    tab_books, tab_authors = st.tabs([f"📚 SÁCH ({len(books_result)})", f"✍️ TÁC GIẢ ({len(authors_result)})"])

    with tab_books:
        if books_result.empty:
            st.info(f"Không tìm thấy sách nào chứa từ khóa '{query}'.")
        else:
            render_book_grid(books_result, "global_books")

    with tab_authors:
        if authors_result.empty:
            st.info(f"Không tìm thấy tác giả nào chứa từ khóa '{query}'.")
        else:
            for start in range(0, len(authors_result), 3):
                cols = st.columns(3)
                for col, (_, author) in zip(cols, authors_result.iloc[start : start + 3].iterrows()):
                    with col:
                        photo_uri = str(author.get("photo_url", "")).strip() or get_author_avatar_placeholder_uri(
                            str(author["name"])
                        )
                        st.markdown(
                            f"""
                            <div class="genre-card">
                                <div style="display:flex; align-items:center; gap:0.8rem; margin-bottom:0.8rem;">
                                    <img src="{photo_uri}" style="width:50px; height:50px; border-radius:50%; object-fit:cover; border:2px solid var(--gold);"/>
                                    <div>
                                        <h4 style="margin:0; font-size:1.05rem;">{html.escape(str(author['name']))}</h4>
                                        <span style="font-size:0.8rem; color:var(--text-muted);">{html.escape(str(author.get('nationality', 'N/A')))}</span>
                                    </div>
                                </div>
                                <p style="font-size:0.85rem; color:var(--text-secondary); flex-grow:1;">{html.escape(str(author.get('bio', ''))[:110])}...</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("Xem tác giả", key=f"global_auth_{author['author_id']}", use_container_width=True):
                            st.session_state.author_id = str(author["author_id"])
                            st.session_state.global_search_open = False
                            navigate("Tác giả")
                            st.rerun()


# ==========================================
# TRANG CHỦ (HERO BANNER & TAB BỐ CỤC 2 CỘT)
# ==========================================
def render_home(books: pd.DataFrame, authors: pd.DataFrame, genres: pd.DataFrame) -> None:
    # 1. Hero Banner Hiện Đại
    available_read_count = len(books[books["reading_available"]]) if "reading_available" in books.columns else 0
    st.markdown(
        f"""
        <section class="hero-banner">
            <div class="hero-badge">
                <span class="hero-badge-dot"></span>
                THƯ VIỆN SỐ THÔNG MINH · TRỢ LÝ AI ĐA PHƯƠNG THỨC
            </div>
            <h1 class="hero-title">Khám Phá Tri Thức & <span>Tư Vấn Sách Thông Minh</span></h1>
            <p class="hero-desc">
                Hệ thống thư viện số hiện đại kết hợp kiến trúc RAG, Google Gemini, nhận diện ảnh bìa qua Computer Vision và đàm thoại giọng nói 2 chiều tiếng Việt.
            </p>
            <div class="hero-stats-grid">
                <div class="hero-stat-item">
                    <div class="hero-stat-num">{len(books)}+</div>
                    <div class="hero-stat-label">Đầu sách chuẩn hóa</div>
                </div>
                <div class="hero-stat-item">
                    <div class="hero-stat-num">768-D</div>
                    <div class="hero-stat-label">ChromaDB RAG Vector</div>
                </div>
                <div class="hero-stat-item">
                    <div class="hero-stat-num">AI Vision</div>
                    <div class="hero-stat-label">Quét bìa tự động</div>
                </div>
                <div class="hero-stat-item">
                    <div class="hero-stat-num">Voice 2-Way</div>
                    <div class="hero-stat-label">STT & TTS Stream MP3</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # 2. Thanh tìm kiếm nhanh nổi bật
    with st.container(border=True):
        col_input, col_submit = st.columns([5, 1.5])
        with col_input:
            home_query = st.text_input(
                "Tìm kiếm sách trong thư viện",
                placeholder="Nhập tên sách, tác giả, thể loại hoặc chủ đề bạn quan tâm...",
                label_visibility="collapsed",
                key="home_search_input",
            )
        with col_submit:
            search_click = st.button("🔍 Tìm sách ngay", type="primary", use_container_width=True)

        if search_click and home_query.strip():
            st.session_state.catalog_query = home_query.strip()
            navigate("Kho sách")
            st.rerun()

    # 3. Bố cục Tabs Linh Hoạt: Trợ lý AI Tư vấn | Khám phá Kho sách | Nổi bật & Thể loại
    home_tab_chat, home_tab_explore, home_tab_featured = st.tabs([
        "🤖 Trợ lý AI Tư vấn (Live Console)",
        "📚 Khám phá Kho sách (Book Explorer)",
        "⭐ Tuyển tập Nổi bật & Thể loại",
    ])

    with home_tab_chat:
        st.markdown(
            """
            <div style="background:var(--surface-white); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:1rem 1.4rem; margin-bottom:1rem;">
                <b style="color:var(--teal-dark); font-size:1.05rem;">Trò chuyện cùng Thủ thư AI trực tiếp tại Trang chủ</b>
                <p style="margin:0.2rem 0 0 0; font-size:0.88rem; color:var(--text-secondary);">
                    Đặt câu hỏi về nội dung, xin gợi ý sách theo tâm trạng hoặc yêu cầu so sánh đa tài liệu. AI sẽ tra cứu ngữ nghĩa ChromaDB và đưa ra câu trả lời chuẩn xác.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Gợi ý nhanh (Quick Chips)
        st.markdown("<p style='font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.4rem;'>💡 <b>Gợi ý câu hỏi bắt đầu:</b></p>", unsafe_allow_html=True)
        chip_cols = st.columns(4)
        suggestions = [
            ("🤖 Sách về AI cho người mới", "Tìm sách về AI cho người mới bắt đầu"),
            ("🌱 Phát triển bản thân", "Tôi muốn tìm sách phát triển bản thân và tư duy tích cực"),
            ("🧠 Tâm lý học hành vi", "Gợi ý sách hay về tâm lý học và thấu hiểu con người"),
            ("⚡ Xây dựng thói quen", "Tìm sách giúp xây dựng thói quen tốt và kỷ luật bản thân"),
        ]
        for col, (label, query_text) in zip(chip_cols, suggestions):
            with col:
                if st.button(label, key=f"chip_home_{label}", use_container_width=True):
                    st.session_state.pending_question = query_text
                    navigate("AI Trợ lý")
                    st.rerun()

        # Hiển thị các tin nhắn gần nhất nếu có
        if st.session_state.messages:
            st.write("")
            for msg_idx, msg in enumerate(st.session_state.messages[-4:]):
                avatar_icon = ":material/person:" if msg["role"] == "user" else ":material/auto_awesome:"
                with st.chat_message(msg["role"], avatar=avatar_icon):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and msg.get("books"):
                        render_retrieved_books(msg["books"], f"home_ret_{msg_idx}")

        chat_cta_cols = st.columns([3, 1])
        with chat_cta_cols[0]:
            quick_q = st.text_input("Nhập câu hỏi để bắt đầu trò chuyện với AI:", placeholder="Ví dụ: Tôi cảm thấy mất tập trung, nên đọc cuốn sách nào?...", key="home_quick_chat_input")
        with chat_cta_cols[1]:
            st.write("")
            if st.button("🚀 Gửi cho AI", type="primary", use_container_width=True):
                if quick_q.strip():
                    st.session_state.pending_question = quick_q.strip()
                    navigate("AI Trợ lý")
                    st.rerun()

    with home_tab_explore:
        st.markdown('<div class="lib-section-title">📚 Danh mục ấn phẩm mới cập nhật</div>', unsafe_allow_html=True)
        explore_books = books.head(9)
        render_book_grid(explore_books, "home_explore")
        if st.button("👉 Xem toàn bộ kho sách (" + str(len(books)) + " cuốn)", use_container_width=True):
            navigate("Kho sách")
            st.rerun()

    with home_tab_featured:
        st.markdown('<div class="lib-section-title">⭐ Tuyển tập sách được độc giả yêu thích</div>', unsafe_allow_html=True)
        featured_df = get_featured_books(books, 6)
        render_book_grid(featured_df, "home_featured")

        st.markdown('<div class="lib-section-title">🏷️ Khám phá theo thể loại</div>', unsafe_allow_html=True)
        g_cols = st.columns(4)
        for col, (_, genre) in zip(g_cols, genres.head(8).iterrows()):
            with col:
                g_books_count = len(books[books["genre"] == genre["name"]]) if "genre" in books.columns else 0
                st.markdown(
                    f"""
                    <div class="genre-card">
                        <div style="font-size:1.5rem; margin-bottom:0.4rem;">📚</div>
                        <h4 style="margin:0 0 0.4rem 0; font-size:1.05rem;">{html.escape(str(genre['name']))}</h4>
                        <p style="font-size:0.83rem; color:var(--text-secondary); flex-grow:1; margin-bottom:0.6rem;">{html.escape(str(genre['description']))}</p>
                        <span style="font-size:0.78rem; font-weight:600; color:var(--teal-primary);">{g_books_count} cuốn sách</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Duyệt thể loại", key=f"home_genre_{genre['genre_id']}", use_container_width=True):
                    st.session_state.genre_filter = genre["name"]
                    navigate("Kho sách")
                    st.rerun()


# ==========================================
# TRANG KHO SÁCH (CATALOG)
# ==========================================
def render_catalog(books: pd.DataFrame, authors: pd.DataFrame, genres: pd.DataFrame) -> None:
    st.markdown('<div class="lib-section-title">📚 Kho sách Thư viện</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<b style='color:var(--slate-dark); font-size:1.05rem;'>Bộ lọc & Tìm kiếm Nâng cao</b>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            query = st.text_input(
                "Từ khóa tìm kiếm",
                value=st.session_state.pop("catalog_query", ""),
                placeholder="Tên sách, tác giả, tags...",
            )
        with col2:
            all_genres = ["Tất cả"] + sorted(books["genre"].unique().tolist())
            def_genre = st.session_state.pop("genre_filter", "Tất cả")
            genre_idx = all_genres.index(def_genre) if def_genre in all_genres else 0
            genre = st.selectbox("Thể loại", all_genres, index=genre_idx)
        with col3:
            all_authors = ["Tất cả"] + sorted(books["author"].unique().tolist())
            author = st.selectbox("Tác giả", all_authors)
        with col4:
            sort_by = st.selectbox("Sắp xếp theo", ["Phù hợp", "Tên A-Z", "Năm mới nhất", "Đánh giá cao"])

        with st.expander("⚙️ Bộ lọc mở rộng (Năm, Ngôn ngữ, Đánh giá, Nổi bật)", expanded=False):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                all_langs = ["Tất cả"] + sorted(books["language"].unique().tolist())
                language = st.selectbox("Ngôn ngữ", all_langs)
            with f_col2:
                lower, upper = int(books["year"].min()), int(books["year"].max())
                year_range = st.slider("Khoảng năm xuất bản", lower, upper, (lower, upper))
            with f_col3:
                min_rating = st.slider("Đánh giá tối thiểu", 0.0, 5.0, 0.0, 0.5)
            with f_col4:
                featured_only = st.checkbox("Chỉ sách nổi bật ⭐")

        result = search_books(
            books,
            query=query,
            genre=genre,
            author=author,
            year_range=year_range,
            language=language,
            min_rating=min_rating,
            featured_only=featured_only,
            sort_by=sort_by,
        )

    # Hiển thị số lượng tìm thấy
    res_cols = st.columns([4, 1])
    with res_cols[0]:
        st.markdown(
            f"<p style='color:var(--text-secondary); margin:0.8rem 0;'>Tìm thấy <b style='color:var(--teal-primary); font-size:1.05rem;'>{len(result)}</b> cuốn sách phù hợp trong kho.</p>",
            unsafe_allow_html=True,
        )
    with res_cols[1]:
        if st.button("↺ Đặt lại bộ lọc", use_container_width=True):
            st.session_state.pop("genre_filter", None)
            st.session_state.pop("catalog_query", None)
            st.rerun()

    render_book_grid(result, "catalog")


# ==========================================
# TRANG CHI TIẾT SÁCH (BOOK DETAIL)
# ==========================================
def render_detail(books: pd.DataFrame, authors: pd.DataFrame) -> None:
    book_id = st.session_state.get("selected_book_id", "")
    book = get_book(books, book_id)
    if not book:
        st.warning("Không tìm thấy thông tin cuốn sách trong thư viện.")
        if st.button("← Quay lại kho sách"):
            navigate("Kho sách")
            st.rerun()
        return

    if st.button("← Quay lại kho sách", key="back_to_catalog"):
        navigate("Kho sách")
        st.rerun()

    # Bố cục 2 cột: Ảnh bìa & Thông tin
    left_col, right_col = st.columns([1.2, 2.8])

    with left_col:
        cover_html = render_cover_image(book, height=360, is_large=True)
        detail_cover_html = textwrap.dedent(
            f"""
            <div style="border-radius:12px; overflow:hidden; box-shadow:var(--shadow-md); margin-bottom:1rem;">
            {cover_html}
            </div>
            """
        ).strip()
        if hasattr(st, "html"):
            st.html(detail_cover_html)
        else:
            st.markdown(detail_cover_html, unsafe_allow_html=True)

        meta_card_html = textwrap.dedent(
            f"""
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
            <span style="color:var(--text-secondary);">Đánh giá:</span>
            <b style="color:var(--gold);">⭐ {book['rating']:.1f} / 5.0</b>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
            <span style="color:var(--text-secondary);">Năm xuất bản:</span>
            <b>{book['year']}</b>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
            <span style="color:var(--text-secondary);">Số trang:</span>
            <b>{book['pages']} trang</b>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
            <span style="color:var(--text-secondary);">Ngôn ngữ:</span>
            <b>{book['language']}</b>
            </div>
            <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-secondary);">Định dạng:</span>
            <b>{book.get('format', 'Bìa mềm')}</b>
            </div>
            """
        ).strip()
        with st.container(border=True):
            if hasattr(st, "html"):
                st.html(meta_card_html)
            else:
                st.markdown(meta_card_html, unsafe_allow_html=True)

    with right_col:
        detail_card_html = textwrap.dedent(
            f"""
            <div class="detail-card">
            <span class="book-genre-chip" style="font-size:0.85rem;">{html.escape(str(book['genre']))}</span>
            <h1 style="color:var(--slate-dark); font-size:2rem; margin:0.3rem 0 0.5rem 0;">{html.escape(str(book['title']))}</h1>
            <h4 style="color:var(--text-secondary); margin:0 0 1rem 0; font-weight:550;">Tác giả: {html.escape(str(book['author']))}</h4>
            <div class="detail-tag-cloud">
            <span class="detail-tag-item">🎯 {html.escape(str(book.get('target_audience', 'Mọi độc giả')))}</span>
            <span class="detail-tag-item">⚡ Độ khó: {html.escape(str(book.get('difficulty', 'Trung bình')))}</span>
            <span class="detail-tag-item gold">💡 Tâm trạng: {html.escape(str(book.get('mood', 'Tích cực')))}</span>
            </div>
            <hr style="border-color:var(--border-light); margin:1rem 0;"/>
            <h4 style="color:var(--teal-dark); margin-bottom:0.4rem;">Mô tả nội dung</h4>
            <p style="color:var(--text-primary); line-height:1.6; margin-bottom:1.2rem;">{html.escape(str(book['description']))}</p>
            <h4 style="color:var(--teal-dark); margin-bottom:0.4rem;">Tóm tắt cốt lõi</h4>
            <p style="color:var(--text-secondary); line-height:1.6; margin-bottom:1.2rem;">{html.escape(str(book['summary']))}</p>
            <p style="font-size:0.85rem; color:var(--text-muted);"><b>Tags:</b> {html.escape(str(book.get('tags', '')))}</p>
            </div>
            """
        ).strip()
        if hasattr(st, "html"):
            st.html(detail_card_html)
        else:
            st.markdown(detail_card_html, unsafe_allow_html=True)

        # Cụm nút hành động chuẩn UI/UX
        act_col1, act_col2, act_col3 = st.columns(3)
        with act_col1:
            if st.button("🤖 Hỏi AI về sách này", type="primary", use_container_width=True):
                navigate("AI Trợ lý")
                st.session_state.pending_question = (
                    f"Hãy cho tôi biết thêm về cuốn '{book['title']}' của tác giả {book['author']} và những điểm nổi bật của cuốn sách này."
                )
                st.rerun()
        with act_col2:
            buy_url = book.get("purchase_url") or purchase_search_url(str(book["title"]))
            st.link_button("🛒 Tìm nơi mua sách", buy_url, use_container_width=True)
        with act_col3:
            if st.button("🗺️ Tìm thư viện / nhà sách", use_container_width=True):
                st.session_state.location_query = str(book["title"])
                navigate("Thư viện & Nhà sách")
                st.rerun()

    # Về tác giả
    author_data = get_author(authors, str(book.get("author_id", "")))
    if author_data:
        st.markdown('<div class="lib-section-title">✍️ Về tác giả</div>', unsafe_allow_html=True)
        with st.container(border=True):
            a_cols = st.columns([1, 5])
            with a_cols[0]:
                auth_photo = str(author_data.get("photo_url", "")).strip() or get_author_avatar_placeholder_uri(
                    str(author_data["name"])
                )
                st.markdown(
                    f'<img src="{auth_photo}" style="width:100%; border-radius:50%; object-fit:cover; border:2px solid var(--gold);"/>',
                    unsafe_allow_html=True,
                )
            with a_cols[1]:
                st.subheader(author_data["name"])
                st.write(author_data.get("bio", "Chưa có tiểu sử chi tiết."))
                if st.button("Xem trang tác giả", key="btn_detail_author_page"):
                    st.session_state.author_id = str(author_data["author_id"])
                    navigate("Tác giả")
                    st.rerun()

    # Trạng thái Đọc sách
    st.markdown('<div class="lib-section-title">📖 Trạng thái bản đọc thư viện</div>', unsafe_allow_html=True)
    status_msg = reading_status(book)
    if can_read(book):
        st.success(f"✓ {status_msg}")
        if st.button("📖 Mở đọc sách trực tuyến", type="primary", key="btn_open_read"):
            st.session_state.reading_book_id = str(book["book_id"])
            navigate("Đọc sách")
            st.rerun()
    else:
        st.info(status_msg)
        if book.get("reading_url"):
            st.link_button("🔗 Mở nguồn đọc hợp pháp", book["reading_url"])

    # Sách tương tự
    st.markdown('<div class="lib-section-title">📚 Sách tương tự cùng chủ đề</div>', unsafe_allow_html=True)
    related_df = get_related_books(books, book, limit=3)
    render_book_grid(related_df, "detail_related")


# ==========================================
# TRANG TÁC GIẢ (AUTHORS)
# ==========================================
def render_authors(books: pd.DataFrame, authors: pd.DataFrame) -> None:
    st.markdown('<div class="lib-section-title">✍️ Tác giả & Tác phẩm</div>', unsafe_allow_html=True)

    author_id = st.session_state.get("author_id", "")
    if author_id:
        author = get_author(authors, author_id)
        if author:
            if st.button("← Quay lại danh sách tác giả"):
                st.session_state.author_id = ""
                st.rerun()

            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    photo_uri = str(author.get("photo_url", "")).strip() or get_author_avatar_placeholder_uri(
                        str(author["name"])
                    )
                    st.markdown(
                        f'<img src="{photo_uri}" style="width:140px; height:140px; border-radius:50%; object-fit:cover; border:3px solid var(--gold); box-shadow:var(--shadow-md);"/>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.title(author["name"])
                    st.caption(f"Quốc tịch: {author.get('nationality', 'N/A')} · Năm sinh: {author.get('birth_year', 'N/A')}")
                    st.write(author.get("bio", "Tiểu sử chưa có sẵn."))

            st.markdown('<div class="lib-section-title">📚 Tác phẩm có trong thư viện</div>', unsafe_allow_html=True)
            auth_books = get_books_by_author(books, author_id)
            render_book_grid(auth_books, "auth_books")
            return

    col_search, _ = st.columns([3, 1])
    with col_search:
        auth_query = st.text_input("Tìm kiếm tác giả", placeholder="Nhập tên tác giả để tìm kiếm...")
    results = search_authors(authors, auth_query)
    st.caption(f"Hiển thị {len(results)} tác giả")

    for start in range(0, len(results), 3):
        cols = st.columns(3)
        for col, (_, author) in zip(cols, results.iloc[start : start + 3].iterrows()):
            with col:
                photo_uri = str(author.get("photo_url", "")).strip() or get_author_avatar_placeholder_uri(
                    str(author["name"])
                )
                auth_work_count = len(get_books_by_author(books, author["author_id"]))
                st.markdown(
                    f"""
                    <div class="genre-card">
                        <div style="display:flex; align-items:center; gap:0.9rem; margin-bottom:0.8rem;">
                            <img src="{photo_uri}" style="width:58px; height:58px; border-radius:50%; object-fit:cover; border:2px solid var(--gold);"/>
                            <div>
                                <h4 style="margin:0; font-size:1.05rem;">{html.escape(str(author['name']))}</h4>
                                <span style="font-size:0.8rem; color:var(--text-muted);">{html.escape(str(author.get('nationality', 'Quốc tế')))}</span>
                            </div>
                        </div>
                        <p style="font-size:0.84rem; color:var(--text-secondary); flex-grow:1; margin-bottom:0.6rem;">{html.escape(str(author.get('bio', ''))[:110])}...</p>
                        <span style="font-size:0.78rem; font-weight:600; color:var(--teal-primary);">{auth_work_count} tác phẩm trong kho</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Xem tác giả", key=f"btn_author_{author['author_id']}", use_container_width=True):
                    st.session_state.author_id = author["author_id"]
                    st.rerun()


# ==========================================
# TRANG THỂ LOẠI (GENRES)
# ==========================================
def render_genres(books: pd.DataFrame, genres: pd.DataFrame) -> None:
    st.markdown('<div class="lib-section-title">🏷️ Danh mục Thể loại Sách</div>', unsafe_allow_html=True)

    selected = st.selectbox("Chọn thể loại để duyệt", ["Tất cả thể loại"] + genres["name"].tolist())
    if selected == "Tất cả thể loại":
        st.caption(f"Thư viện hiện đang tổ chức {len(genres)} thể loại đa dạng.")
        g_cols = st.columns(3)
        for index, (_, genre) in enumerate(genres.iterrows()):
            col_target = g_cols[index % 3]
            with col_target:
                g_count = len(books[books["genre"] == genre["name"]])
                st.markdown(
                    f"""
                    <div class="genre-card">
                        <h4 style="margin:0 0 0.4rem 0;">📚 {html.escape(str(genre['name']))}</h4>
                        <p style="font-size:0.85rem; color:var(--text-secondary); flex-grow:1;">{html.escape(str(genre['description']))}</p>
                        <span style="font-size:0.8rem; font-weight:600; color:var(--teal-primary);">{g_count} cuốn sách</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Xem sách thể loại này", key=f"genre_btn_{genre['genre_id']}", use_container_width=True):
                    st.session_state.genre_filter = genre["name"]
                    navigate("Kho sách")
                    st.rerun()
        return

    genre_row = genres[genres["name"] == selected].iloc[0]
    st.info(f"💡 {genre_row['description']}")
    books_in_genre = books[books["genre"] == selected].sort_values("rating", ascending=False)
    st.caption(f"Tìm thấy {len(books_in_genre)} cuốn sách thuộc thể loại {selected}.")
    render_book_grid(books_in_genre, "genre_page")


# ==========================================
# TRANG ĐỌC SÁCH (READER)
# ==========================================
def render_reading(books: pd.DataFrame) -> None:
    st.markdown('<div class="lib-section-title">📖 Trình Đọc Sách Số Hóa Hợp Pháp</div>', unsafe_allow_html=True)
    selected_id = st.session_state.get("reading_book_id", "")

    if selected_id:
        selected_book = get_book(books, selected_id)
        if selected_book:
            if st.button("← Quay lại chi tiết sách", key="back_from_reader_page"):
                st.session_state.selected_book_id = selected_id
                navigate("Chi tiết sách")
                st.rerun()

            st.markdown(
                f"""
                <div style="background:var(--surface-white); border:1px solid var(--border-light); border-left:4px solid var(--teal-primary); padding:1rem 1.4rem; border-radius:var(--radius-md); margin-bottom:1.2rem;">
                    <h3 style="margin:0; color:var(--slate-dark);">{html.escape(str(selected_book['title']))}</h3>
                    <p style="margin:0.2rem 0 0 0; color:var(--text-secondary);">Tác giả: {html.escape(str(selected_book['author']))} · Thể loại: {html.escape(str(selected_book['genre']))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            local_file = validate_local_file(str(selected_book.get("local_file", "")))
            if local_file and can_read(selected_book):
                if local_file.suffix.lower() == ".pdf":
                    st.pdf(local_file.read_bytes(), height=750)
                else:
                    st.info("Tệp EPUB đã được xác thực an toàn. Bạn có thể tải về để đọc trên các thiết bị chuyên dụng.")
                    st.download_button(
                        "📥 Tải tệp EPUB hợp pháp",
                        data=local_file.read_bytes(),
                        file_name=local_file.name,
                        mime="application/epub+zip",
                        key=f"dl_epub_{selected_id}",
                        type="primary",
                    )
            else:
                st.info("📖 Sách này hiện chưa có bản điện tử trong thư viện.")
            return

    available = books[books["reading_available"]]
    if available.empty:
        st.info("Thư viện hiện chưa có file đọc toàn văn được cấp phép công khai. Bạn có thể mở nguồn mua hoặc catalog hợp pháp từ trang chi tiết sách.")
        return

    st.markdown(
        """
        <div style="background:var(--teal-subtle); border-left:4px solid var(--teal-primary); padding:0.9rem 1.2rem; border-radius:var(--radius-sm); margin-bottom:1.2rem;">
            <b>Chính sách thư viện số:</b> Chỉ những tệp đọc hợp pháp được lưu trữ an toàn trong <code>data/sample_books</code> và được cấp phép mới có thể mở toàn văn.
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_book_grid(available, "reading_catalog")


# ==========================================
# TRANG BẢN ĐỒ / THƯ VIỆN & NHÀ SÁCH
# ==========================================
def render_locations() -> None:
    st.markdown('<div class="lib-section-title">🗺️ Tìm Thư Viện & Nhà Sách Thực Tế</div>', unsafe_allow_html=True)
    st.caption("Dữ liệu địa điểm thực tế được tra cứu chính xác qua SerpApi Google Maps Engine.")

    with st.form("loc_form", border=True):
        f_cols = st.columns([3, 2, 2])
        with f_cols[0]:
            location = st.text_input(
                "Khu vực / Thành phố",
                value=st.session_state.pop("location_query", ""),
                placeholder="Ví dụ: Đà Nẵng, Huế, Hà Nội, TP.HCM...",
            )
        with f_cols[1]:
            kind_label = st.selectbox("Loại địa điểm", ["Nhà sách", "Thư viện"])
        with f_cols[2]:
            limit = st.slider("Số lượng kết quả", 3, 10, 6)
        submitted = st.form_submit_button("🔍 Tìm kiếm địa điểm", type="primary", use_container_width=True)

    if submitted:
        if not location.strip():
            st.warning("Vui lòng nhập thành phố hoặc khu vực cần tìm.")
            return
        try:
            with st.spinner("Đang tra cứu Google Maps..."):
                results = (
                    search_libraries(location, limit) if kind_label == "Thư viện" else search_bookstores(location, limit)
                )
                st.session_state.location_results = results
                st.session_state.location_kind = kind_label
                st.session_state.location_area = location.strip()
        except LocationServiceError as error:
            st.session_state.location_results = []
            st.error(str(error))
            return

    results = st.session_state.get("location_results", [])
    if results:
        st.success(f"Tìm thấy {len(results)} địa điểm tại khu vực '{st.session_state.get('location_area', '')}'.")
        map_points = [
            {"lat": item["latitude"], "lon": item["longitude"]}
            for item in results
            if isinstance(item.get("latitude"), (int, float)) and isinstance(item.get("longitude"), (int, float))
        ]
        if map_points:
            st.map(pd.DataFrame(map_points))

        for index, item in enumerate(results):
            with st.container(border=True):
                st.markdown(f"**📍 {html.escape(str(item['title']))}**")
                if item.get("address"):
                    st.write(f"Địa chỉ: {item['address']}")
                if item.get("rating"):
                    st.write(f"⭐ Đánh giá: {item['rating']}/5 ({item.get('reviews', 0)} lượt đánh giá)")
                if item.get("open_state") or item.get("hours"):
                    st.write(f"🕒 Giờ mở cửa: {item.get('open_state') or item.get('hours')}")
                if item.get("phone"):
                    st.write(f"☎️ Hotline: {item['phone']}")
                actions = st.columns(2 if item.get("website") else 1)
                actions[0].link_button(
                    "🧭 Chỉ đường trên Google Maps",
                    item.get("directions_url") or item["google_maps_url"],
                    use_container_width=True,
                )
                if item.get("website"):
                    actions[1].link_button("🌐 Ghé thăm Website", item["website"], use_container_width=True)
    elif not submitted:
        st.info("Nhập khu vực và nhấn 'Tìm kiếm địa điểm' để bắt đầu.")


# ==========================================
# TRANG AI TRỢ LÝ (BỐ CỤC 2 CỘT CHUYÊN NGHIỆP)
# ==========================================
def render_chat() -> None:
    st.markdown('<div class="lib-section-title">🤖 Trợ lý Thủ thư AI (Gemini Grounded RAG)</div>', unsafe_allow_html=True)
    st.caption("AI hỗ trợ tìm kiếm ngữ nghĩa, giải đáp thắc mắc, phân tích cảm xúc và gợi ý sách cá nhân hóa dựa trên dữ liệu thư viện.")

    # Bố cục 2 Cột: Cột trái (70%) là Chat Console, Cột phải (30%) là Multimodal Toolbox
    chat_col, tool_col = st.columns([2.5, 1.2])

    with tool_col:
        # 1. Hộp công cụ AI Vision
        with st.container(border=True):
            st.markdown("<b>📸 Quét ảnh bìa sách (Vision AI)</b>", unsafe_allow_html=True)
            st.caption("Tải ảnh bìa (JPG, PNG) để Gemini Vision tự đọc tiêu đề và tìm trong kho.")
            uploaded_file = st.file_uploader(
                "Chọn ảnh bìa", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="chat_vision_uploader"
            )
            if uploaded_file is not None:
                image = PIL.Image.open(uploaded_file)
                st.image(image, caption="Ảnh tải lên", use_container_width=True)
                if st.button("🔍 Quét & Tìm sách", type="primary", use_container_width=True, key="btn_vision_scan"):
                    with st.spinner("AI Vision đang đọc ảnh bìa..."):
                        try:
                            gemini_key = get_gemini_api_key()
                            if not gemini_key:
                                st.error("Chưa cấu hình GEMINI_API_KEY!")
                            else:
                                genai.configure(api_key=gemini_key)
                                vision_model = genai.GenerativeModel("gemini-2.5-flash")
                                prompt = "Bạn là thủ thư. Hãy đọc chữ trên ảnh bìa sách này và trích xuất đúng tên cuốn sách (và tác giả nếu thấy). Tuyệt đối chỉ in ra tên sách, không giải thích dài dòng."
                                response = vision_model.generate_content([prompt, image])
                                extracted_title = response.text.strip()
                                st.success(f"✨ AI đọc được: **{extracted_title}**")
                                st.session_state.pending_question = f"Hãy tìm cho tôi cuốn sách có tên: {extracted_title}"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi nhận diện ảnh: {e}")

        # 2. Hộp công cụ Giọng nói (STT)
        with st.container(border=True):
            st.markdown("<b>🎙️ Nhập bằng giọng nói (STT)</b>", unsafe_allow_html=True)
            st.caption("Bấm nút để nói tiếng Việt trực tiếp:")
            spoken_text = speech_to_text(
                language="vi-VN",
                start_prompt="🎙️ Bấm để nói",
                stop_prompt="🛑 Đang lắng nghe...",
                just_once=True,
                key="STT_tool",
            )
            if spoken_text:
                st.session_state.pending_question = spoken_text
                st.rerun()

        # 3. Thông số RAG & Thao tác nhanh
        with st.container(border=True):
            st.markdown("<b>⚙️ Trạng thái AI Grounding</b>", unsafe_allow_html=True)
            try:
                vec_count = get_library_book_count()
                st.caption(f"Kho tri thức: **{vec_count}** vector ChromaDB")
            except Exception:
                st.caption("ChromaDB chưa nạp dữ liệu.")
            st.caption(f"Top-K truy xuất: **{st.session_state.get('top_k', TOP_K_DEFAULT)}** sách")

            if st.button("🗑️ Xóa tin nhắn phiên này", use_container_width=True):
                st.session_state.messages = []
                st.session_state.reader_profile = create_reader_profile()
                st.session_state.user_location = ""
                st.session_state.pending_location_kind = ""
                st.rerun()

    with chat_col:
        # Gợi ý câu hỏi bắt đầu nếu chưa có tin nhắn
        if not st.session_state.messages:
            st.markdown("<p style='font-size:0.88rem; color:var(--text-secondary); margin-bottom:0.4rem;'>💡 <b>Câu hỏi mẫu để bắt đầu:</b></p>", unsafe_allow_html=True)
            chip_cols = st.columns(3)
            suggestions = [
                "Tìm sách về AI cho người mới bắt đầu",
                "Tôi muốn tìm sách phát triển bản thân",
                "Tìm sách giúp xây dựng thói quen tốt",
            ]
            for col, text in zip(chip_cols, suggestions):
                with col:
                    if st.button(text, key=f"chip_chat_{text[:15]}", use_container_width=True):
                        st.session_state.pending_question = text
                        st.rerun()

        # Lịch sử tin nhắn
        for message_index, message in enumerate(st.session_state.messages):
            avatar_icon = ":material/person:" if message["role"] == "user" else ":material/auto_awesome:"
            with st.chat_message(message["role"], avatar=avatar_icon):
                st.markdown(message["content"])
                if message["role"] == "assistant" and message.get("books"):
                    render_retrieved_books(message["books"], f"hist_source_{message_index}")
                if message["role"] == "assistant" and message.get("location"):
                    render_location_results(message["location"], f"hist_loc_{message_index}")

        # Input & Xử lý câu hỏi
        pending = st.session_state.pop("pending_question", "")
        question = st.chat_input("Hỏi thủ thư AI về sách, tác giả hoặc chủ đề cần đọc...") or pending

        if not question:
            return

        # Lưu và hiển thị câu hỏi của User
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(question)

        # Xử lý phản hồi của Assistant
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            try:
                intent = classify_intent(question, st.session_state.messages[:-1])
                location_result = None
                explicit_location = extract_user_location(question)

                if intent == SET_LOCATION and not explicit_location:
                    explicit_location = question.strip().rstrip("?.!")
                if explicit_location:
                    st.session_state.user_location = normalize_user_location(explicit_location)

                if intent == SET_LOCATION:
                    if st.session_state.pending_location_kind:
                        pending_kind = st.session_state.pending_location_kind
                        answer, st.session_state.user_location, location_result = process_pending_location(
                            question, pending_kind, st.session_state.user_location
                        )
                        if location_result:
                            st.session_state.pending_location_kind = ""
                    else:
                        answer = f"Đã ghi nhận khu vực của bạn là **{st.session_state.user_location}**. Bạn có thể yêu cầu mình tìm nhà sách hoặc thư viện gần đó."
                    retrieved = []
                elif intent in {FIND_BOOKSTORE, FIND_LIBRARY, LOCATION_SEARCH}:
                    if not explicit_location and not st.session_state.user_location:
                        st.session_state.pending_location_kind = "library" if intent == FIND_LIBRARY else "bookstore"
                        answer = "Bạn đang ở khu vực nào? Ví dụ: Đà Nẵng, Huế hoặc Hà Nội."
                        retrieved = []
                    else:
                        answer, location_result = handle_location_request(question, st.session_state.user_location)
                        retrieved = []
                elif intent == LOCATION_HELP:
                    answer = "Bạn đang ở khu vực nào? Ví dụ: Đà Nẵng, Huế hoặc Hà Nội."
                    retrieved = []
                else:
                    with st.spinner("AI Thủ thư đang tra cứu và suy luận..."):
                        answer, retrieved, _ = handle_user_message(
                            question,
                            st.session_state.top_k,
                            st.session_state.messages[:-1],
                            st.session_state.reader_profile,
                        )

                st.markdown(answer)

                # Phát âm thanh câu trả lời (TTS)
                audio_bytes = text_to_speech(answer)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)

                if retrieved:
                    render_retrieved_books(retrieved, f"live_source_{len(st.session_state.messages)}")
                if location_result:
                    try:
                        render_location_results(location_result, f"live_loc_{len(st.session_state.messages)}")
                    except Exception:
                        LOGGER.exception("Chat location result rendering failed: keys=%s", list(location_result.keys()))
                        st.error("Dữ liệu địa điểm đã được truy vấn nhưng giao diện chưa thể hiển thị kết quả.")

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "books": retrieved, "location": location_result}
                )
                save_chat_session(st.session_state.username, st.session_state.current_session_id, st.session_state.messages)

            except LocationServiceError:
                LOGGER.exception("Chat location search failed")
                st.error("Hiện tại mình không thể truy vấn dữ liệu địa điểm. Bạn có thể thử lại sau.")
            except (ValueError, RuntimeError):
                LOGGER.exception("AI request failed")
                st.error("Xin lỗi, hệ thống AI tạm thời chưa thể xử lý yêu cầu này. Bạn có thể thử lại sau ít giây.")


# ==========================================
# KHỞI TẠO STATE & DATA
# ==========================================
init_state()
_b_mtime = os.path.getmtime("data/books.csv") if os.path.exists("data/books.csv") else 0.0
_a_mtime = os.path.getmtime("data/authors.csv") if os.path.exists("data/authors.csv") else 0.0
_g_mtime = os.path.getmtime("data/genres.csv") if os.path.exists("data/genres.csv") else 0.0
books, authors, genres = load_library_data(_b_mtime, _a_mtime, _g_mtime)

# ==========================================
# GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ (PREMIUM)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    c_pad1, c_box, c_pad2 = st.columns([1, 1.8, 1])
    with c_box:
        st.markdown(
            """
            <div style="background:var(--surface-white); border:1px solid var(--border-light); border-top:5px solid var(--teal-primary); border-radius:var(--radius-lg); padding:2.2rem 2.4rem; box-shadow:var(--shadow-lg); text-align:center;">
                <div style="font-size:3rem; margin-bottom:0.5rem;">📚</div>
                <h2 style="color:var(--slate-dark); margin:0 0 0.4rem 0;">AI DIGITAL LIBRARY</h2>
                <p style="color:var(--text-secondary); font-size:0.92rem; margin:0 0 1.5rem 0;">Hệ thống thư viện số thông minh & Trợ lý Tri thức RAG Đa phương thức</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            tab_login, tab_reg = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký"])
            with tab_login:
                with st.form("login_form"):
                    login_user = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập của bạn")
                    login_pass = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
                    if st.form_submit_button("Đăng nhập vào thư viện", type="primary", use_container_width=True):
                        if verify_login(login_user, login_pass):
                            st.session_state.logged_in = True
                            st.session_state.username = login_user
                            st.session_state.current_session_id = str(uuid.uuid4())
                            st.rerun()
                        else:
                            st.error("Tên đăng nhập hoặc mật khẩu không đúng!")
            with tab_reg:
                with st.form("register_form"):
                    reg_user = st.text_input("Tên đăng nhập mới", placeholder="Chọn tên đăng nhập")
                    reg_pass = st.text_input("Mật khẩu mới", type="password", placeholder="Tạo mật khẩu an toàn")
                    reg_pass_confirm = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
                    if st.form_submit_button("Tạo tài khoản mới", use_container_width=True):
                        if not reg_user or not reg_pass:
                            st.error("Vui lòng điền đầy đủ thông tin!")
                        elif reg_pass != reg_pass_confirm:
                            st.error("Mật khẩu xác nhận không khớp!")
                        else:
                            if register_user(reg_user, reg_pass):
                                st.success("Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.")
                            else:
                                st.error("Tên đăng nhập đã tồn tại, vui lòng chọn tên khác.")
    st.stop()


# ==========================================
# SIDEBAR HIỆN ĐẠI
# ==========================================
with st.sidebar:
    st.markdown(
        """
        <div style="padding:0.5rem 0 0.8rem 0;">
            <div style="display:flex; align-items:center; gap:0.7rem;">
                <span style="font-size:1.9rem;">📚</span>
                <div>
                    <h3 style="margin:0; font-size:1.15rem; color:#FFFFFF;">TRI THỨC SỐ</h3>
                    <span style="font-size:0.75rem; color:#6EE7B7; letter-spacing:0.04em;">HỆ THỐNG THÔNG MINH</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"{len(books)} cuốn sách · {len(authors)} tác giả · {len(genres)} thể loại")

    # Thông tin tài khoản
    st.divider()
    st.markdown(f"**👤 Tài khoản:** `{st.session_state.username}`")
    col_out, col_new = st.columns(2)
    with col_out:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.rerun()
    with col_new:
        if st.button("➕ Chat mới", type="primary", use_container_width=True):
            st.session_state.current_session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.page = "AI Trợ lý"
            st.rerun()

    # Menu Điều hướng chính
    st.divider()
    pages = [
        "Trang chủ",
        "Kho sách",
        "Chi tiết sách",
        "Tác giả",
        "Thể loại",
        "Sách nổi bật",
        "AI Trợ lý",
        "Đọc sách",
        "Thư viện & Nhà sách",
        "AI Crawler",
    ]
    if st.session_state.get("pending_navigation") in pages:
        st.session_state.navigation = st.session_state.pop("pending_navigation")
    selected_page = st.selectbox(
        "Điều hướng hệ thống",
        pages,
        index=pages.index(st.session_state.navigation) if st.session_state.navigation in pages else 0,
        key="navigation",
    )
    st.session_state.page = selected_page

    # Lịch sử cuộc trò chuyện
    st.divider()
    st.markdown("**💬 Lịch sử trò chuyện**")
    past_chats = load_all_chats(st.session_state.username)
    if not past_chats:
        st.caption("Chưa có lịch sử trò chuyện.")
    else:
        for chat in past_chats:
            col_c, col_d = st.columns([4.5, 1])
            with col_c:
                if st.button(f"💬 {chat['title']}", key=f"chat_{chat['id']}", use_container_width=True):
                    st.session_state.current_session_id = chat["id"]
                    st.session_state.messages = chat["messages"]
                    st.session_state.page = "AI Trợ lý"
                    st.rerun()
            with col_d:
                if st.button("🗑️", key=f"del_{chat['id']}", help="Xóa đoạn chat"):
                    delete_chat_session(st.session_state.username, chat["id"])
                    if st.session_state.current_session_id == chat["id"]:
                        st.session_state.current_session_id = str(uuid.uuid4())
                        st.session_state.messages = []
                    st.rerun()

    # Cấu hình RAG Top-K & Trạng thái
    with st.expander("⚙️ Cấu hình AI RAG", expanded=False):
        st.session_state.top_k = st.slider(
            "Số sách Top-K truy xuất", 1, MAX_TOP_K, st.session_state.get("top_k", TOP_K_DEFAULT)
        )
        try:
            st.caption(f"Vector Database: {get_library_book_count()} bản ghi ChromaDB")
        except Exception:
            st.caption("ChromaDB chưa được ingest.")
        if st.button("Xóa tin nhắn phiên này", use_container_width=True, key="sidebar_clear_chat"):
            st.session_state.messages = []
            st.session_state.reader_profile = create_reader_profile()
            st.session_state.user_location = ""
            st.session_state.pending_location_kind = ""
            st.rerun()


# ==========================================
# AI CRAWLER PAGE (BẢO TOÀN NGUYÊN VẸN 100%)
# ==========================================
def render_crawler() -> None:  # noqa: C901 — intentionally single function for page
    """Render the AI Crawler admin page."""
    import os

    st.html(textwrap.dedent("""
        <div style="
            background: linear-gradient(135deg, #0B1F3A 0%, #123B66 100%);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 18px;
        ">
            <div style="font-size: 2.5rem;">🤖</div>
            <div>
                <div style="color: #C9A227; font-size: 0.85rem; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 4px;">Tính năng nâng cao</div>
                <div style="color: #ffffff; font-size: 1.6rem; font-weight: 700; margin-bottom: 6px;">AI Crawler — Bổ sung sách tự động</div>
                <div style="color: #a8c4e0; font-size: 0.95rem;">Tìm kiếm sách từ Open Library và iTunes, kiểm tra trùng lặp và nhập thẳng vào thư viện.</div>
            </div>
        </div>
    """).strip())

    # ── Recovery & Synchronization Panel ──────────────────────────────────
    unindexed = get_unindexed_books()
    if unindexed:
        st.warning(f"⚠️ Phát hiện **{len(unindexed)}** sách trong CSV chưa được tạo embedding trong ChromaDB (do lỗi mạng hoặc bước embedding trước bị gián đoạn).")
        col_sync1, col_sync2 = st.columns([2, 1])
        with col_sync1:
            st.caption(f"Danh sách chưa index: {', '.join([b.get('title', '') for b in unindexed[:3]])}{'...' if len(unindexed) > 3 else ''}")
        with col_sync2:
            if st.button("🔄 Đồng bộ lại vào ChromaDB", key="crawler_sync_unindexed", type="secondary", use_container_width=True):
                api_key = os.getenv("GEMINI_API_KEY", "").strip()
                if not api_key:
                    st.error("❌ Không tìm thấy GEMINI_API_KEY trong .env.")
                else:
                    sync_progress = st.progress(0, text="⚙️ Đang đồng bộ...")
                    def _sync_cb(curr, tot):
                        sync_progress.progress(curr / tot if tot else 1, text=f"Đang đồng bộ {curr}/{tot}...")
                    with st.spinner("Đang bổ sung vectors vào ChromaDB..."):
                        sync_res = sync_unindexed_books_to_chroma(api_key, progress_callback=_sync_cb)
                    sync_progress.progress(1.0, text="Đã hoàn tất đồng bộ!")
                    load_library_data.clear()
                    st.success(f"✅ Đã đồng bộ thành công {sync_res.get('upserted', 0)}/{sync_res.get('total_unindexed', 0)} sách!")
                    st.rerun()

    # ── Filters ────────────────────────────────────────────────────────────
    with st.expander("🔍 Bộ lọc tìm kiếm & Nguồn dữ liệu", expanded=True):
        col_src, col_q, col_auth = st.columns([1.5, 2, 1.8])
        with col_src:
            source = st.selectbox(
                "Nguồn dữ liệu",
                [
                    "Tất cả nguồn (Tìm kiếm kết hợp)",
                    "Open Library",
                    "Google Books",
                    "Project Gutenberg (Đọc toàn văn)",
                    "Internet Archive",
                    "Apple Books (Ebook VN)",
                    "Europeana (Di sản Châu Âu)",
                ],
                key="crawler_source",
            )
        with col_q:
            query = st.text_input(
                "Từ khóa / Tên sách",
                placeholder="Ví dụ: python, kinh tế học, tâm lý...",
                key="crawler_query",
            )
        with col_auth:
            author_q = st.text_input(
                "Tác giả",
                placeholder="Ví dụ: Dale Carnegie...",
                key="crawler_author",
            )

        col_subj, col_isbn, col_lang, col_yr1, col_yr2, col_lim = st.columns([1.8, 1.2, 1, 1, 1, 1])
        with col_subj:
            subject = st.text_input(
                "Chủ đề / Thể loại",
                placeholder="psychology, fiction...",
                key="crawler_subject",
            )
        with col_isbn:
            isbn_input = st.text_input(
                "ISBN",
                placeholder="0132100673...",
                key="crawler_isbn",
            )
        with col_lang:
            lang_opt = st.selectbox(
                "Ngôn ngữ",
                ["(Tất cả)", "vie", "eng", "fra"],
                key="crawler_lang",
            )
            lang_val = "" if lang_opt == "(Tất cả)" else lang_opt
        with col_yr1:
            year_from = st.number_input("Từ năm", min_value=1800, max_value=2030, value=1900, step=1, key="crawler_yr1")
        with col_yr2:
            year_to = st.number_input("Đến năm", min_value=1800, max_value=2030, value=2026, step=1, key="crawler_yr2")
        with col_lim:
            limit = st.number_input("Số lượng", min_value=5, max_value=100, value=20, step=5, key="crawler_limit")

        search_clicked = st.button("🚀 Bắt đầu thu thập", type="primary", use_container_width=True)

    # ── Run search ─────────────────────────────────────────────────────────
    if search_clicked:
        if not query.strip() and not author_q.strip() and not subject.strip() and not isbn_input.strip():
            st.warning("⚠️ Vui lòng nhập ít nhất một từ khóa, tên tác giả, chủ đề hoặc mã ISBN.")
        else:
            source_map_key = {
                "Tất cả nguồn (Tìm kiếm kết hợp)": "all",
                "Open Library": "open_library",
                "Google Books": "google_books",
                "Project Gutenberg (Đọc toàn văn)": "gutenberg",
                "Internet Archive": "internet_archive",
                "Apple Books (Ebook VN)": "itunes",
                "Europeana (Di sản Châu Âu)": "europeana",
            }
            source_key = source_map_key.get(source, "all")
            with st.spinner(f"⏳ Đang thu thập dữ liệu từ {source}..."):
                try:
                    results = crawl_and_prepare(
                        source=source_key,
                        query=query.strip(),
                        author=author_q.strip(),
                        subject=subject.strip(),
                        isbn=isbn_input.strip(),
                        language=lang_val,
                        year_from=int(year_from) if int(year_from) > 1800 else 0,
                        year_to=int(year_to) if int(year_to) < 2030 else 0,
                        limit=int(limit),
                    )
                    st.session_state.crawler_results = results
                    st.session_state.crawler_source_label = source
                    st.session_state.crawler_selected_ids = []
                except Exception as exc:
                    st.error(f"❌ Lỗi khi thu thập: {exc}")
                    st.session_state.crawler_results = []


    # ── Display results ─────────────────────────────────────────────────────
    results: list[dict] = st.session_state.get("crawler_results", [])
    if not results:
        if not search_clicked:
            st.html(textwrap.dedent("""
                <div style="text-align:center; padding: 48px 0; color: #8899aa;">
                    <div style="font-size: 3rem; margin-bottom: 12px;">📡</div>
                    <div style="font-size: 1.1rem; font-weight: 600;">Chưa có kết quả</div>
                    <div style="font-size: 0.9rem; margin-top: 4px;">Nhập bộ lọc phía trên rồi nhấn "Bắt đầu thu thập".</div>
                </div>
            """).strip())
        return

    # Stats bar
    n_total = len(results)
    n_new = sum(1 for r in results if r.get("status") == "new")
    n_dup = sum(1 for r in results if r.get("status") == "duplicate")
    n_unc = sum(1 for r in results if r.get("status") == "uncertain")
    n_no_desc = sum(1 for r in results if not str(r.get("description", "")).strip())

    st.html(textwrap.dedent(f"""
        <div style="display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap;">
            <div style="background:#EAF1F8; border-radius:10px; padding:12px 20px; flex:1; min-width:100px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:700; color:#0B1F3A;">{n_total}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">Tổng kết quả</div>
            </div>
            <div style="background:#e8f5e9; border-radius:10px; padding:12px 20px; flex:1; min-width:100px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:700; color:#1b5e20;">{n_new}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">Sách mới</div>
            </div>
            <div style="background:#fff3e0; border-radius:10px; padding:12px 20px; flex:1; min-width:100px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:700; color:#bf360c;">{n_dup}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">Trùng lặp</div>
            </div>
            <div style="background:#fff8e1; border-radius:10px; padding:12px 20px; flex:1; min-width:100px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:700; color:#e65100;">{n_unc}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">Cần xem xét</div>
            </div>
            <div style="background:#fce4ec; border-radius:10px; padding:12px 20px; flex:1; min-width:100px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:700; color:#880e4f;">{n_no_desc}</div>
                <div style="font-size:0.8rem; color:#555; margin-top:2px;">Thiếu mô tả</div>
            </div>
        </div>
    """).strip())

    # Selection helpers
    st.markdown("**📋 Chọn sách để nhập vào thư viện**")
    help_cols = st.columns([1, 1, 3])
    with help_cols[0]:
        if st.button("☑️ Chọn tất cả mới", key="crawler_sel_all"):
            st.session_state.crawler_selected_ids = [
                i for i, r in enumerate(results) if r.get("status") == "new"
            ]
            st.rerun()
    with help_cols[1]:
        if st.button("☐ Bỏ chọn tất cả", key="crawler_desel_all"):
            st.session_state.crawler_selected_ids = []
            st.rerun()

    selected_ids: list[int] = st.session_state.get("crawler_selected_ids", [])

    # Status badge HTML helper
    _STATUS_BADGE = {
        "new": '<span style="background:#1b5e20;color:#fff;border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:600;">✅ Mới</span>',
        "duplicate": '<span style="background:#bf360c;color:#fff;border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:600;">🔁 Trùng</span>',
        "uncertain": '<span style="background:#e65100;color:#fff;border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:600;">⚠️ Xem xét</span>',
    }

    # Results table (row per book)
    for idx, record in enumerate(results):
        status = record.get("status", "new")
        badge = _STATUS_BADGE.get(status, "")
        reason = record.get("match_reason", "")
        title = record.get("title", "(Không tên)")
        author_val = record.get("author", "")
        genre = record.get("genre", "")
        year_val = record.get("year", "")
        cover = record.get("cover_url", "")
        rating_val = record.get("rating", 0.0)

        with st.container():
            row_cols = st.columns([0.4, 0.8, 3.5, 1.5, 1, 0.8])
            with row_cols[0]:
                # Checkbox to select
                checked = idx in selected_ids
                new_checked = st.checkbox(
                    " ", value=checked,
                    key=f"crawler_chk_{idx}",
                    disabled=(status == "duplicate"),
                )
                if new_checked and idx not in selected_ids:
                    selected_ids.append(idx)
                    st.session_state.crawler_selected_ids = selected_ids
                elif not new_checked and idx in selected_ids:
                    selected_ids.remove(idx)
                    st.session_state.crawler_selected_ids = selected_ids
            with row_cols[1]:
                # Cover thumbnail
                if cover:
                    st.image(cover, width=55)
                else:
                    st.html('<div style="width:55px;height:75px;background:#EAF1F8;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;">📚</div>')
            with row_cols[2]:
                st.markdown(f"**{html.escape(title)}**")
                source_tag = record.get("_source", "")
                source_badge = f'<span style="background:#e0e7ff;color:#1e3a8a;border-radius:4px;padding:1px 6px;font-size:0.7rem;font-weight:600;margin-right:6px;">🌐 {html.escape(source_tag)}</span>' if source_tag else ""
                reading_badge = '<span style="background:#dcfce7;color:#166534;border-radius:4px;padding:1px 6px;font-size:0.7rem;font-weight:600;">📖 Đọc trực tuyến</span>' if record.get("reading_available") else ""
                st.html(f'<div style="margin-bottom:4px;">{source_badge}{reading_badge}</div>')
                st.caption(f"{html.escape(author_val)} · {html.escape(str(genre))} · {year_val}")
                if reason:
                    st.caption(f"🔎 {reason}")
            with row_cols[3]:
                st.html(f'<div style="margin-top:8px;">{badge}</div>')
            with row_cols[4]:
                st.caption(f"⭐ {rating_val:.1f}")
            with row_cols[5]:
                lib_url = record.get("library_url", "")
                purch_url = record.get("purchase_url", "")
                link = lib_url or purch_url
                if link:
                    st.link_button("🔗", link, help="Xem trên nguồn gốc")
        st.divider()

    # ── Import section ──────────────────────────────────────────────────────
    n_selected = len(st.session_state.get("crawler_selected_ids", []))
    st.markdown(f"**{n_selected} sách được chọn để nhập**")

    do_embed = st.checkbox(
        "🧠 Cập nhật ChromaDB (embedding — cần API key, mất ~1 giây/sách)",
        value=False,
        key="crawler_do_embed",
    )

    if st.button(
        f"📥 Xác nhận nhập {n_selected} sách vào thư viện",
        type="primary",
        disabled=(n_selected == 0),
        key="crawler_confirm_import",
    ):
        sel_idx = st.session_state.get("crawler_selected_ids", [])
        books_to_import = [results[i] for i in sel_idx if i < len(results)]

        # Remove status/match_reason keys before CSV write
        clean_books = []
        for b in books_to_import:
            clean = {k: b.get(k, "") for k in CRAWLER_BOOK_FIELDS}
            clean_books.append(clean)

        with st.spinner("💾 Đang lưu vào CSV..."):
            csv_stats = save_books_to_csv(clean_books)

        st.html(textwrap.dedent(f"""
            <div style="background:#e8f5e9;border-radius:10px;padding:14px 20px;margin:8px 0;">
                <b>✅ Kết quả lưu CSV:</b>&nbsp;
                Đã lưu <b>{csv_stats['saved']}</b> sách &nbsp;|&nbsp;
                Bỏ qua (trùng): <b>{csv_stats['skipped']}</b> &nbsp;|&nbsp;
                Lỗi: <b>{csv_stats['errors']}</b>
            </div>
        """).strip())

        if do_embed and csv_stats["saved"] > 0:
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                st.error("❌ Không tìm thấy GEMINI_API_KEY trong .env. Bỏ qua bước embedding.")
            else:
                # Only embed books that were actually saved
                import pandas as _pd
                try:
                    fresh_df = _pd.read_csv("data/books.csv").fillna("")
                    saved_titles = {b.get("title", "").strip() for b in clean_books}
                    embed_books = fresh_df[fresh_df["title"].isin(saved_titles)].to_dict("records")
                except Exception:
                    embed_books = clean_books

                progress_bar = st.progress(0, text="⚙️ Đang tạo embedding...")
                total_embed = len(embed_books)
                embed_done = [0]

                def _progress_cb(current: int, total: int) -> None:
                    embed_done[0] = current
                    pct = current / total if total else 1
                    progress_bar.progress(pct, text=f"⚙️ Đang embedding {current}/{total}...")

                with st.spinner("🧠 Đang cập nhật ChromaDB..."):
                    embed_stats = ingest_books_to_chroma(
                        books_to_ingest=embed_books,
                        gemini_api_key=api_key,
                        progress_callback=_progress_cb,
                    )
                progress_bar.progress(1.0, text="✅ Hoàn tất!")
                st.html(textwrap.dedent(f"""
                    <div style="background:#e3f2fd;border-radius:10px;padding:14px 20px;margin:8px 0;">
                        <b>🧠 Kết quả ChromaDB:</b>&nbsp;
                        Đã upsert <b>{embed_stats['upserted']}</b> vectors &nbsp;|&nbsp;
                        Thất bại: <b>{embed_stats['failed']}</b>
                    </div>
                """).strip())

        # Clear selection, cached results and data cache after import
        st.session_state.crawler_results = []
        st.session_state.crawler_selected_ids = []
        load_library_data.clear()
        st.success("🎉 Hoàn tất! Chuyển sang trang Kho sách để xem sách vừa nhập.")
        if st.button("📚 Xem Kho sách", key="crawler_goto_catalog"):
            navigate("Kho sách")
            st.rerun()


# ==========================================
# THANH ĐIỀU HƯỚNG TRÊN CÙNG: TÌM KIẾM TOÀN CỤC
# ==========================================
with st.container():
    bar_cols = st.columns([1.5, 3.5, 1])
    with bar_cols[0]:
        if st.button(f"📖 {st.session_state.page}", key="home_logo_btn", help="Quay về màn hình chính"):
            navigate("Trang chủ")
            st.session_state.global_search_open = False 
            st.rerun()
    with bar_cols[1]:
        g_search_val = st.text_input(
            "Tìm kiếm toàn cục...",
            placeholder="🔍 Tìm nhanh sách hoặc tác giả trong thư viện...",
            label_visibility="collapsed",
            key="global_search_input_box",
        )
    with bar_cols[2]:
        if st.button("Tìm toàn cục", type="primary", use_container_width=True):
            if g_search_val.strip():
                st.session_state.global_search_query = g_search_val.strip()
                st.session_state.global_search_open = True
                st.rerun()

# ==========================================
# ĐIỀU HƯỚNG TRANG CHÍNH
# ==========================================
if st.session_state.get("global_search_open") and st.session_state.get("global_search_query"):
    render_global_search_view(books, authors)
else:
    page = st.session_state.page
    if page == "Trang chủ":
        render_home(books, authors, genres)
    elif page == "Kho sách":
        render_catalog(books, authors, genres)
    elif page == "Chi tiết sách":
        render_detail(books, authors)
    elif page == "Tác giả":
        render_authors(books, authors)
    elif page == "Thể loại":
        render_genres(books, genres)
    elif page == "Sách nổi bật":
        st.markdown('<div class="lib-section-title">⭐ Tuyển tập Sách nổi bật</div>', unsafe_allow_html=True)
        render_book_grid(get_featured_books(books, len(books)), "all_featured")
    elif page == "AI Trợ lý":
        render_chat()
    elif page == "Đọc sách":
        render_reading(books)
    elif page == "Thư viện & Nhà sách":
        render_locations()
    elif page == "AI Crawler":
        render_crawler()
