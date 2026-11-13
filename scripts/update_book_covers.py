import json
import time
import shutil
import unicodedata
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOKS_CSV = PROJECT_ROOT / "data" / "books.csv"
SELECTED_BOOKS_CSV = PROJECT_ROOT / "data" / "selected_books.csv"
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "openlibrary"
COVERS_BASE = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
SEARCH_URL = "https://openlibrary.org/search.json"
HEADERS = {"User-Agent": "BookRecommenderChatbot/1.0 (Open Library cover updater)"}
REQUEST_DELAY = 1.0
SEARCH_LIMIT = 5


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.split())


def clean_olid(value):
    if value is None:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    value = value.replace("https://openlibrary.org", "")
    for prefix in ("/works/", "/authors/"):
        if value.startswith(prefix):
            return value.split(prefix, 1)[1].split(".", 1)[0]
    if value.startswith("OL"):
        return value.split(".", 1)[0]
    return ""


def make_cover_url(cover_id):
    if cover_id is None or str(cover_id).strip() == "":
        return ""
    try:
        cover_id_int = int(float(str(cover_id).strip()))
    except (ValueError, TypeError):
        return ""
    return COVERS_BASE.format(cover_id=cover_id_int) if cover_id_int > 0 else ""


def get_json(url, params=None):
    response = requests.get(url, params=params, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.json()


def load_selected_books():
    if not SELECTED_BOOKS_CSV.exists():
        return {}
    df = pd.read_csv(SELECTED_BOOKS_CSV, dtype=str).fillna("")
    result = {}
    for _, row in df.iterrows():
        catalog_id = str(row.get("catalog_book_id", "")).strip()
        if catalog_id:
            result[catalog_id] = {
                "openlibrary_work_id": clean_olid(row.get("openlibrary_work_id", "")),
                "preferred_edition_id": clean_olid(row.get("preferred_edition_id", "")),
            }
    return result


def find_cover_from_raw(work_id, edition_id):
    candidates = []
    if edition_id:
        candidates.append(RAW_ROOT / "editions" / f"{edition_id}.json")
    if work_id:
        candidates.extend([
            RAW_ROOT / "works" / f"{work_id}.json",
            RAW_ROOT / "editions" / f"{work_id}.json",
        ])
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cover_url = make_cover_url(data.get("cover_i"))
        if cover_url:
            return cover_url
        covers = data.get("covers")
        if isinstance(covers, list):
            for cover in covers:
                cover_url = make_cover_url(cover)
                if cover_url:
                    return cover_url
    return ""


def title_match_score(book_title, result_title):
    a, b = normalize_text(book_title), normalize_text(result_title)
    if not a or not b:
        return 0
    if a == b:
        return 100
    if a in b or b in a:
        return 80
    aw, bw = set(a.split()), set(b.split())
    return int(len(aw & bw) / max(len(aw), len(bw)) * 60) if aw and bw else 0


def author_match_score(book_author, result_authors):
    target = normalize_text(book_author)
    best = 0
    for author in result_authors or []:
        candidate = normalize_text(author)
        if target and candidate == target:
            best = max(best, 40)
        elif target and (target in candidate or candidate in target):
            best = max(best, 25)
    return best


def search_cover(book_title, book_author):
    queries = []
    if book_title and book_author:
        queries.append(f'title:"{book_title}" author:"{book_author}"')
    if book_title:
        queries.append(book_title)

    for query in dict.fromkeys(queries):
        try:
            data = get_json(SEARCH_URL, params={
                "q": query,
                "limit": SEARCH_LIMIT,
                "fields": "key,title,author_name,cover_i",
            })
        except requests.RequestException as exc:
            print(f"  ! Open Library search lỗi: {exc}")
            continue

        scored = []
        for doc in data.get("docs", []):
            cover_url = make_cover_url(doc.get("cover_i"))
            score = title_match_score(book_title, doc.get("title", ""))
            score += author_match_score(book_author, doc.get("author_name", []))
            if cover_url:
                score += 10
            scored.append((score, cover_url))
        scored.sort(key=lambda x: x[0], reverse=True)

        for score, cover_url in scored:
            if cover_url and score >= 60:
                return cover_url
        if book_author:
            for score, cover_url in scored:
                if cover_url:
                    return cover_url
    return ""


def main():
    if not BOOKS_CSV.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {BOOKS_CSV}")

    df = pd.read_csv(BOOKS_CSV, dtype=str).fillna("")
    required = {"title", "cover_url"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"books.csv thiếu cột: {', '.join(sorted(missing))}")

    backup_path = BOOKS_CSV.with_suffix(".csv.bak")
    shutil.copy2(BOOKS_CSV, backup_path)
    selected_books = load_selected_books()

    total = len(df)
    already_have = found_raw = found_api = not_found = 0

    print("=" * 60)
    print("CẬP NHẬT ẢNH BÌA SÁCH TỪ OPEN LIBRARY")
    print("=" * 60)

    for index, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        author = str(row.get("author_name", row.get("author", ""))).strip()
        current_cover = str(row.get("cover_url", "")).strip()

        if current_cover:
            already_have += 1
            print(f"[{index + 1}/{total}] ĐÃ CÓ: {title}")
            continue

        print(f"[{index + 1}/{total}] ĐANG TÌM: {title}")
        catalog_id = str(row.get("book_id", "")).strip()
        selected = selected_books.get(catalog_id, {})
        work_id = clean_olid(selected.get("openlibrary_work_id", "") or row.get("openlibrary_work_id", ""))
        edition_id = clean_olid(selected.get("preferred_edition_id", "") or row.get("preferred_edition_id", ""))

        cover_url = find_cover_from_raw(work_id, edition_id)
        if cover_url:
            df.at[index, "cover_url"] = cover_url
            found_raw += 1
            print(f"  + Raw: {cover_url}")
            continue

        cover_url = search_cover(title, author)
        if cover_url:
            df.at[index, "cover_url"] = cover_url
            found_api += 1
            print(f"  + Open Library: {cover_url}")
        else:
            not_found += 1
            print("  - Chưa tìm được ảnh bìa.")
        time.sleep(REQUEST_DELAY)

    df.to_csv(BOOKS_CSV, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print("HOÀN TẤT")
    print("=" * 60)
    print(f"Tổng số sách       : {total}")
    print(f"Đã có cover trước  : {already_have}")
    print(f"Tìm từ raw         : {found_raw}")
    print(f"Tìm từ Open Library: {found_api}")
    print(f"Chưa có cover      : {not_found}")
    print(f"File cập nhật      : {BOOKS_CSV}")
    print(f"File backup        : {backup_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
