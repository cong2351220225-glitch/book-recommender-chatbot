"""
Test Suite: Phase 3.3.2B Continue Reading Progress Hotfix Verification
Classified into:
- Unit Test: Tests mathematical progress calculation, bounds clamping [0.0, 1.0], and null/zero safety.
- Static Wiring Test: Verifies that home_screen.dart integrates with BookshelfProvider and removes hardcoded 0.45.
- Real Integration Test: Verifies live reading progress calculation, persistence, and multi-book independence.
"""

import math
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ==============================================================================
# 1. UNIT TESTS: Progress Calculation Logic & Boundary Safety
# ==============================================================================

def calculate_reading_progress(current_page: int | None, total_pages: int | None) -> tuple[float, int, str]:
    """
    Python mirror of the Dart progress calculation logic implemented in home_screen.dart.
    """
    curr = current_page if (current_page is not None and current_page >= 0) else 0
    total = total_pages if (total_pages is not None and total_pages > 0) else 0

    progress = 0.0
    if total > 0:
        progress = curr / total
        if math.isnan(progress) or math.isinf(progress):
            progress = 0.0
        elif progress > 1.0:
            progress = 1.0
        elif progress < 0.0:
            progress = 0.0

    percent = round(progress * 100)
    if total > 0:
        label = f"Trang {curr} / {total} ({percent}%)"
    elif curr > 0:
        label = f"Đã đọc đến trang {curr}"
    else:
        label = "Mới bắt đầu đọc (0%)"

    return progress, percent, label


def test_unit_progress_standard_cases():
    # 45/300 trang phải hiển thị 15%
    p1, pct1, lbl1 = calculate_reading_progress(45, 300)
    assert p1 == 0.15
    assert pct1 == 15
    assert lbl1 == "Trang 45 / 300 (15%)"

    # 0/300 trang phải hiển thị 0%
    p2, pct2, lbl2 = calculate_reading_progress(0, 300)
    assert p2 == 0.0
    assert pct2 == 0
    assert lbl2 == "Trang 0 / 300 (0%)"

    # 300/300 trang phải hiển thị 100%
    p3, pct3, lbl3 = calculate_reading_progress(300, 300)
    assert p3 == 1.0
    assert pct3 == 100
    assert lbl3 == "Trang 300 / 300 (100%)"


def test_unit_progress_edge_cases_safety():
    # total_pages bằng 0 hoặc null
    p0, pct0, lbl0 = calculate_reading_progress(10, 0)
    assert p0 == 0.0
    assert pct0 == 0
    assert lbl0 == "Đã đọc đến trang 10"

    p_null, pct_null, lbl_null = calculate_reading_progress(0, None)
    assert p_null == 0.0
    assert pct_null == 0
    assert lbl_null == "Mới bắt đầu đọc (0%)"

    # Không hiển thị giá trị âm
    p_neg, pct_neg, _ = calculate_reading_progress(-5, 200)
    assert p_neg == 0.0
    assert pct_neg == 0

    # Không vượt 100%
    p_over, pct_over, _ = calculate_reading_progress(350, 300)
    assert p_over == 1.0
    assert pct_over == 100


# ==============================================================================
# 2. STATIC WIRING TESTS: home_screen.dart inspection
# ==============================================================================

def test_static_wiring_hardcoded_progress_removed():
    with open("mobile_app/lib/presentation/screens/home_screen.dart", "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT contain hardcoded value: 0.45 anymore
    assert "value: 0.45" not in content

    # Must import bookshelf provider
    assert "bookshelf_provider.dart" in content

    # Must find item dynamically from bookshelf provider
    assert "findItem(item.bookId, 'reading')" in content

    # Must use dynamic progress variable in LinearProgressIndicator
    assert "LinearProgressIndicator(\n                                  value: progress," in content or "value: progress" in content

    # Must refresh bookshelf on resume from reader
    assert "context.read<BookshelfProvider>().loadBookshelf(silent: true)" in content


# ==============================================================================
# 3. REAL INTEGRATION TESTS: Backend sync & Independent book progress
# ==============================================================================

def test_real_integration_independent_books_progress_and_update():
    """
    [Real Integration Test]
    Flow:
    1. Register unique user.
    2. Add book_001 (45/300) -> 15%.
    3. Add book_002 (150/200) -> 75%.
    4. Verify both books return distinct, independent progress.
    5. Update progress for book_001 to 90/300.
    6. Verify updated progress is 30% without affecting book_002.
    """
    test_user = f"hotfix_user_{uuid.uuid4().hex[:6]}"
    password = "HotfixPassword123!"

    client.post("/api/v1/auth/register", json={"username": test_user, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": test_user, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add book_001: 45 / 300
    res1 = client.post(
        "/api/v1/bookshelf",
        headers=headers,
        json={"book_id": "book_001", "status": "reading", "progress_page": 45, "total_pages": 300},
    )
    assert res1.status_code in [200, 201]

    # Add book_002: 150 / 200
    res2 = client.post(
        "/api/v1/bookshelf",
        headers=headers,
        json={"book_id": "book_002", "status": "reading", "progress_page": 150, "total_pages": 200},
    )
    assert res2.status_code in [200, 201]

    # Get bookshelf items
    get_res = client.get("/api/v1/bookshelf?status=reading", headers=headers)
    assert get_res.status_code == 200
    items = get_res.json().get("items", [])
    assert len(items) == 2

    item_map = {it["book_id"]: it for it in items}
    assert item_map["book_001"]["progress_page"] == 45
    assert item_map["book_001"]["total_pages"] == 300
    assert item_map["book_002"]["progress_page"] == 150
    assert item_map["book_002"]["total_pages"] == 200

    # Calculate percentages
    pct1 = round((item_map["book_001"]["progress_page"] / item_map["book_001"]["total_pages"]) * 100)
    pct2 = round((item_map["book_002"]["progress_page"] / item_map["book_002"]["total_pages"]) * 100)
    assert pct1 == 15
    assert pct2 == 75

    # Update progress for book_001 via reading API
    update_res = client.post(
        "/api/v1/reading/progress",
        headers=headers,
        json={"book_id": "book_001", "current_page": 90, "total_pages": 300},
    )
    assert update_res.status_code in [200, 201]

    # Verify updated progress on bookshelf
    updated_shelf_res = client.get("/api/v1/bookshelf?status=reading", headers=headers)
    assert updated_shelf_res.status_code == 200
    updated_items = updated_shelf_res.json().get("items", [])
    updated_map = {it["book_id"]: it for it in updated_items}

    assert updated_map["book_001"]["progress_page"] == 90
    assert updated_map["book_002"]["progress_page"] == 150  # book_002 unchanged!

    new_pct1 = round((updated_map["book_001"]["progress_page"] / updated_map["book_001"]["total_pages"]) * 100)
    assert new_pct1 == 30
