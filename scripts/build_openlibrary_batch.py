from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SELECTED_FILE = DATA / "selected_books.csv"
BOOKS_FILE = DATA / "books.csv"
AUTHORS_FILE = DATA / "authors.csv"
GENRES_FILE = DATA / "genres.csv"
MANIFEST_FILE = DATA / "source_manifest.csv"

RAW = DATA / "raw" / "openlibrary"
WORKS_DIR = RAW / "works"
EDITIONS_DIR = RAW / "editions"
AUTHORS_DIR = RAW / "authors"
INDEXES_DIR = RAW / "indexes"

for folder in (WORKS_DIR, EDITIONS_DIR, AUTHORS_DIR, INDEXES_DIR):
    folder.mkdir(parents=True, exist_ok=True)


BASE_URL = "https://openlibrary.org"

HEADERS = {
    "User-Agent": "BookRecommenderChatbot/1.0"
}

BOOK_COLUMNS = [
    "book_id",
    "title",
    "author",
    "author_id",
    "genre",
    "description",
    "year",
    "isbn",
    "publisher",
    "pages",
    "language",
    "format",
    "cover_url",
    "rating",
    "featured",
    "tags",
    "target_audience",
    "mood",
    "difficulty",
    "summary",
    "reading_available",
    "reading_type",
    "reading_url",
    "local_file",
    "purchase_url",
    "library_url",
]

AUTHOR_COLUMNS = [
    "author_id",
    "name",
    "bio",
    "nationality",
    "birth_year",
    "death_year",
    "photo_url",
    "website",
    "featured",
]

MANIFEST_COLUMNS = [
    "entity_type",
    "entity_id",
    "book_id",
    "work_id",
    "edition_id",
    "author_id",
    "endpoint_url",
    "raw_path",
    "fetched_at_utc",
    "http_status",
    "sha256",
    "parser_version",
    "selection_policy_version",
    "selected",
    "error",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_json(url: str, retries: int = 3) -> tuple[int, Any]:
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30,
            )

            if response.status_code == 200:
                return response.status_code, response.json()

            if response.status_code == 404:
                return 404, None

            last_error = f"HTTP {response.status_code}"

        except requests.RequestException as exc:
            last_error = str(exc)

        time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(last_error or "Open Library request failed")


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        return str(value.get("value", "")).strip()

    return str(value).strip()


def extract_year(value: Any) -> str:
    text = clean_text(value)
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b", text)

    return match.group(1) if match else ""


def extract_author_ids(work: dict) -> list[str]:
    result = []

    for item in work.get("authors", []):
        author = item.get("author", {})

        key = author.get("key", "")

        if key.startswith("/authors/"):
            author_id = key.split("/")[-1]

            if author_id and author_id not in result:
                result.append(author_id)

    return result


def extract_subjects(work: dict) -> str:
    subjects = work.get("subjects", [])

    values = []

    for subject in subjects:
        if isinstance(subject, str):
            value = subject.strip()
        else:
            value = clean_text(subject)

        if value and value not in values:
            values.append(value)

    return ", ".join(values[:20])


def choose_edition(editions: list[dict], preferred_id: str, preferred_language: str) -> dict | None:
    if preferred_id:
        for edition in editions:
            if edition.get("key", "").endswith(preferred_id):
                return edition

    candidates = editions

    if preferred_language:
        language_filtered = []

        for edition in candidates:
            languages = edition.get("languages", [])

            language_keys = [
                x.get("key", "").split("/")[-1]
                for x in languages
                if isinstance(x, dict)
            ]

            if preferred_language in language_keys:
                language_filtered.append(edition)

        if language_filtered:
            candidates = language_filtered

    if not candidates:
        return None

    # Ưu tiên edition có ISBN + publish date.
    def score(edition: dict) -> int:
        score_value = 0

        if edition.get("isbn"):
            score_value += 3

        if edition.get("isbn_13"):
            score_value += 3

        if edition.get("publish_date"):
            score_value += 2

        if edition.get("publishers"):
            score_value += 1

        if edition.get("number_of_pages"):
            score_value += 1

        return score_value

    return sorted(candidates, key=score, reverse=True)[0]


def get_isbn(edition: dict) -> str:
    isbn13 = edition.get("isbn_13", [])
    isbn10 = edition.get("isbn_10", [])

    if isbn13:
        return str(isbn13[0])

    if isbn10:
        return str(isbn10[0])

    identifiers = edition.get("identifiers", {})

    if identifiers.get("isbn_13"):
        return str(identifiers["isbn_13"][0])

    if identifiers.get("isbn_10"):
        return str(identifiers["isbn_10"][0])

    return ""


def get_language(edition: dict) -> str:
    languages = edition.get("languages", [])

    if not languages:
        return ""

    key = languages[0].get("key", "")

    mapping = {
        "eng": "Tiếng Anh",
        "vie": "Tiếng Việt",
        "fra": "Tiếng Pháp",
        "deu": "Tiếng Đức",
        "spa": "Tiếng Tây Ban Nha",
        "ita": "Tiếng Ý",
        "jpn": "Tiếng Nhật",
        "kor": "Tiếng Hàn",
        "chi": "Tiếng Trung",
    }

    code = key.split("/")[-1]

    return mapping.get(code, code)


def get_cover_url(work: dict, edition: dict | None) -> str:
    cover_ids = []

    if edition:
        cover_ids.extend(edition.get("covers", []) or [])

    cover_ids.extend(work.get("covers", []) or [])

    for cover_id in cover_ids:
        if cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

    return ""


def build_author_row(author_id: str, author_data: dict) -> dict:
    photos = author_data.get("photos", []) or []

    photo_url = ""

    if photos:
        photo_url = (
            f"https://covers.openlibrary.org/a/id/"
            f"{photos[0]}-M.jpg"
        )

    bio = clean_text(author_data.get("bio"))

    return {
        "author_id": author_id.lower().replace("_", "-"),
        "name": clean_text(author_data.get("name")),
        "bio": bio,
        "nationality": "",
        "birth_year": extract_year(author_data.get("birth_date")),
        "death_year": extract_year(author_data.get("death_date")),
        "photo_url": photo_url,
        "website": "",
        "featured": False,
    }


def append_manifest(
    manifest: list[dict],
    *,
    entity_type: str,
    entity_id: str,
    book_id: str,
    work_id: str = "",
    edition_id: str = "",
    author_id: str = "",
    endpoint_url: str,
    raw_path: Path,
    http_status: int,
    selected: bool,
    error: str = "",
) -> None:
    manifest.append(
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "book_id": book_id,
            "work_id": work_id,
            "edition_id": edition_id,
            "author_id": author_id,
            "endpoint_url": endpoint_url,
            "raw_path": str(raw_path.relative_to(ROOT)),
            "fetched_at_utc": now_utc(),
            "http_status": http_status,
            "sha256": sha256_file(raw_path) if raw_path.exists() else "",
            "parser_version": "1.0",
            "selection_policy_version": "1.0",
            "selected": selected,
            "error": error,
        }
    )


def main() -> None:
    print("=" * 70)
    print("OPEN LIBRARY BATCH BUILDER")
    print("=" * 70)

    selected = pd.read_csv(SELECTED_FILE, dtype=str).fillna("")

    selected["catalog_book_id"] = selected["catalog_book_id"].str.strip()

    new_rows = selected[
        selected["catalog_book_id"].str.match(r"^book_\d{3}$")
    ].copy()

    print(f"\nSố sách batch cần xử lý: {len(new_rows)}")

    if new_rows.empty:
        print("Không có book_026 → book_060 trong selected_books.csv")
        return

    existing_books = pd.read_csv(BOOKS_FILE, dtype=str).fillna("")
    existing_authors = pd.read_csv(AUTHORS_FILE, dtype=str).fillna("")

    books = existing_books.to_dict("records")
    authors = existing_authors.to_dict("records")

    existing_book_ids = {
        row["book_id"]
        for row in books
    }

    existing_author_ids = {
        row["author_id"]
        for row in authors
    }

    manifest = []

    successful = 0
    failed = 0

    for _, selected_row in new_rows.iterrows():
        book_id = selected_row["catalog_book_id"]
        work_id = selected_row["openlibrary_work_id"].strip()
        preferred_edition_id = selected_row["preferred_edition_id"].strip()
        preferred_language = selected_row["preferred_language"].strip()
        genre_id = selected_row["genre_id"].strip()

        print(f"\n[{book_id}] {work_id}")

        if book_id in existing_book_ids:
            print("  -> Đã tồn tại, bỏ qua.")
            continue

        if not work_id:
            print("  -> THIẾU Work ID")
            failed += 1
            continue

        try:
            # ------------------------------------------------------------
            # WORK
            # ------------------------------------------------------------
            work_url = f"{BASE_URL}/works/{work_id}.json"
            status, work = get_json(work_url)

            if status != 200 or not work:
                print("  -> Work không tồn tại.")
                failed += 1
                continue

            work_path = WORKS_DIR / f"{work_id}.json"
            save_json(work_path, work)

            append_manifest(
                manifest,
                entity_type="work",
                entity_id=work_id,
                book_id=book_id,
                work_id=work_id,
                endpoint_url=work_url,
                raw_path=work_path,
                http_status=status,
                selected=True,
            )

            # ------------------------------------------------------------
            # EDITIONS
            # ------------------------------------------------------------
            editions_url = f"{BASE_URL}/works/{work_id}/editions.json"
            status, editions_data = get_json(editions_url)

            editions = []

            if status == 200 and editions_data:
                editions = editions_data.get("entries", []) or []

            editions_path = INDEXES_DIR / f"{work_id}-editions.json"
            save_json(editions_path, editions_data or {})

            append_manifest(
                manifest,
                entity_type="edition_index",
                entity_id=work_id,
                book_id=book_id,
                work_id=work_id,
                endpoint_url=editions_url,
                raw_path=editions_path,
                http_status=status,
                selected=True,
            )

            edition = choose_edition(
                editions,
                preferred_edition_id,
                preferred_language,
            )

            edition_id = ""

            if edition:
                edition_key = edition.get("key", "")

                if edition_key.startswith("/books/"):
                    edition_id = edition_key.split("/")[-1]
                elif edition_key.startswith("/books/"):
                    edition_id = edition_key.split("/")[-1]

                if edition_id:
                    edition_url = f"{BASE_URL}/books/{edition_id}.json"

                    ed_status, edition_full = get_json(edition_url)

                    if ed_status == 200 and edition_full:
                        edition = edition_full

                        edition_path = EDITIONS_DIR / f"{edition_id}.json"
                        save_json(edition_path, edition)

                        append_manifest(
                            manifest,
                            entity_type="edition",
                            entity_id=edition_id,
                            book_id=book_id,
                            work_id=work_id,
                            edition_id=edition_id,
                            endpoint_url=edition_url,
                            raw_path=edition_path,
                            http_status=ed_status,
                            selected=True,
                        )

            # ------------------------------------------------------------
            # AUTHORS
            # ------------------------------------------------------------
            author_ids = extract_author_ids(work)

            if not author_ids:
                print("  -> Không tìm thấy tác giả.")
                failed += 1
                continue

            author_rows = []

            for author_id in author_ids:
                author_url = f"{BASE_URL}/authors/{author_id}.json"

                a_status, author_data = get_json(author_url)

                author_path = AUTHORS_DIR / f"{author_id}.json"

                if a_status == 200 and author_data:
                    save_json(author_path, author_data)

                    append_manifest(
                        manifest,
                        entity_type="author",
                        entity_id=author_id,
                        book_id=book_id,
                        work_id=work_id,
                        edition_id=edition_id,
                        author_id=author_id,
                        endpoint_url=author_url,
                        raw_path=author_path,
                        http_status=a_status,
                        selected=True,
                    )

                    author_row = build_author_row(
                        author_id,
                        author_data,
                    )

                    author_rows.append(author_row)

                    if author_row["author_id"] not in existing_author_ids:
                        authors.append(author_row)
                        existing_author_ids.add(author_row["author_id"])

            if not author_rows:
                print("  -> Không lấy được dữ liệu tác giả.")
                failed += 1
                continue

            # ------------------------------------------------------------
            # BUILD BOOK
            # ------------------------------------------------------------
            title = clean_text(work.get("title"))

            description = clean_text(work.get("description"))

            if not title or not description:
                print("  -> Thiếu title hoặc description nguồn.")
                failed += 1
                continue

            author_names = [
                x["name"]
                for x in author_rows
                if x["name"]
            ]

            author_name = "; ".join(author_names)

            primary_author_id = author_rows[0]["author_id"]

            year = extract_year(work.get("first_publish_date"))

            if not year and edition:
                year = extract_year(
                    edition.get("publish_date")
                )

            isbn = ""
            publisher = ""
            pages = ""
            language = ""
            book_format = ""

            if edition:
                isbn = get_isbn(edition)

                publishers = edition.get("publishers", []) or []

                if publishers:
                    publisher = clean_text(publishers[0])

                pages_value = (
                    edition.get("number_of_pages")
                    or edition.get("pagination")
                )

                pages = clean_text(pages_value)

                language = get_language(edition)

                book_format = clean_text(
                    edition.get("physical_format")
                )

            cover_url = get_cover_url(work, edition)

            tags = extract_subjects(work)

            genre_name = genre_id

            if GENRES_FILE.exists():
                genres = pd.read_csv(
                    GENRES_FILE,
                    dtype=str,
                ).fillna("")

                found = genres[
                    genres["genre_id"].astype(str).str.strip()
                    == genre_id
                ]

                if not found.empty:
                    genre_name = found.iloc[0]["name"]

            book_row = {
                "book_id": book_id,
                "title": title,
                "author": author_name,
                "author_id": primary_author_id,
                "genre": genre_name,
                "description": description,
                "year": year,
                "isbn": isbn,
                "publisher": publisher,
                "pages": pages,
                "language": language,
                "format": book_format,
                "cover_url": cover_url,
                "rating": "0.0",
                "featured": "False",
                "tags": tags,
                "target_audience": "",
                "mood": "",
                "difficulty": "",
                "summary": "",
                "reading_available": "False",
                "reading_type": "",
                "reading_url": "",
                "local_file": "",
                "purchase_url": "",
                "library_url": "",
            }

            books.append(book_row)
            existing_book_ids.add(book_id)

            successful += 1

            print(f"  -> OK: {title}")
            print(f"  -> Author: {author_name}")
            print(f"  -> Edition: {edition_id or 'none'}")

            time.sleep(0.5)

        except Exception as exc:
            print(f"  -> ERROR: {exc}")
            failed += 1

    # ------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------
    books_df = pd.DataFrame(books)

    for column in BOOK_COLUMNS:
        if column not in books_df.columns:
            books_df[column] = ""

    books_df = books_df[BOOK_COLUMNS]

    books_df.to_csv(
        BOOKS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    authors_df = pd.DataFrame(authors)

    for column in AUTHOR_COLUMNS:
        if column not in authors_df.columns:
            authors_df[column] = ""

    authors_df = authors_df[AUTHOR_COLUMNS]

    authors_df.to_csv(
        AUTHORS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    if manifest:
        manifest_df = pd.DataFrame(manifest)

        for column in MANIFEST_COLUMNS:
            if column not in manifest_df.columns:
                manifest_df[column] = ""

        manifest_df = manifest_df[MANIFEST_COLUMNS]

        manifest_df.to_csv(
            MANIFEST_FILE,
            index=False,
            encoding="utf-8-sig",
        )

    # ------------------------------------------------------------
    # FINAL REPORT
    # ------------------------------------------------------------
    print("\n" + "=" * 70)
    print("KẾT QUẢ BATCH")
    print("=" * 70)

    print(f"Sách xử lý thành công : {successful}")
    print(f"Sách lỗi              : {failed}")
    print(f"Tổng books.csv        : {len(books_df)}")
    print(f"Tổng authors.csv      : {len(authors_df)}")
    print(f"Manifest              : {MANIFEST_FILE}")

    if len(books_df) == 60:
        print("\nĐẠT: books.csv hiện có đúng 60 sách.")
    else:
        print(
            f"\nCHƯA ĐẠT: books.csv hiện có {len(books_df)} sách."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()