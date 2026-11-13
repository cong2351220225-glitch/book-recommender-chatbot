"""
Test Suite: Phase 3.3.2B - Flutter Recommendation UI Integrity & Wiring Tests
Verifies that the Flutter UI components are correctly implemented according to specifications:
- home_screen.dart: Continue reading section, For You recommendation section, Like/Dislike feedback, guest handling.
- book_detail_screen.dart: Similar books section, loadSimilar integration, navigation.
- profile_screen.dart: Genre preferences selection, reading goal setting, updatePreferences integration.
"""

import os
import re
import pytest

HOME_SCREEN_PATH = "mobile_app/lib/presentation/screens/home_screen.dart"
DETAIL_SCREEN_PATH = "mobile_app/lib/presentation/screens/book_detail_screen.dart"
PROFILE_SCREEN_PATH = "mobile_app/lib/presentation/screens/profile_screen.dart"


def test_flutter_ui_files_exist():
    assert os.path.exists(HOME_SCREEN_PATH), f"Missing {HOME_SCREEN_PATH}"
    assert os.path.exists(DETAIL_SCREEN_PATH), f"Missing {DETAIL_SCREEN_PATH}"
    assert os.path.exists(PROFILE_SCREEN_PATH), f"Missing {PROFILE_SCREEN_PATH}"


def test_home_screen_imports_and_providers():
    with open(HOME_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "recommendation_provider.dart" in content
    assert "RecommendationProvider" in content
    assert "AuthProvider" in content


def test_home_screen_continue_reading_section():
    with open(HOME_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Tiếp Tục Mạch Đọc" in content or "tiếp tục mạch đọc" in content.lower()
    assert "DigitalReaderScreen" in content
    assert "LinearProgressIndicator" in content
    assert "loadContinueReading" in content


def test_home_screen_for_you_section():
    with open(HOME_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain For You AI recommendation
    assert "AI Gợi Ý Dành Riêng Cho Bạn" in content
    assert "loadForYou" in content
    assert "_buildRecommendedBookCard" in content or "forYouList" in content
    assert "likeBook" in content
    assert "dislikeBook" in content
    assert "restoreBook" in content


def test_home_screen_new_user_and_guest_banner():
    with open(HOME_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Must handle cold-start or onboarding banner
    assert "Bạn muốn gợi ý chuẩn xác hơn? Hãy chọn các thể loại bạn yêu thích tại mục Hồ sơ" in content
    assert "Khám Phá Sách Được Đề Xuất" in content


def test_book_detail_similar_books_section():
    with open(DETAIL_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "recommendation_provider.dart" in content
    assert "loadSimilar" in content
    assert "Có Thể Bạn Cũng Thích" in content
    assert "_buildSimilarBookCard" in content


def test_profile_screen_preferences_section():
    with open(PROFILE_SCREEN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "recommendation_provider.dart" in content
    assert "genre_provider.dart" in content
    assert "Sở Thích Đọc Sách & Mục Tiêu" in content
    assert "FilterChip" in content
    assert "_goalController" in content
    assert "_selectedGenres" in content
    assert "updatePreferences" in content


def test_colors_and_design_consistency():
    for path in [HOME_SCREEN_PATH, DETAIL_SCREEN_PATH, PROFILE_SCREEN_PATH]:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "AppColors" in content
