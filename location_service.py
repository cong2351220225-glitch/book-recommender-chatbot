from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
SERPAPI_URL = "https://serpapi.com/search.json"
DEFAULT_TIMEOUT = 15


class LocationServiceError(RuntimeError):
    """A user-safe error raised while searching for real locations."""


def build_google_maps_search_url(kind: str, location: str) -> str:
    """Build a Google Maps search URL for use as a reliable fallback."""
    normalized_kind = str(kind or "").strip().lower()
    normalized_location = str(location or "").strip()
    if normalized_kind in {"library", "thuvien", "thu vien", "thư viện", "thu_vien"}:
        label = "thư viện"
    elif normalized_kind in {"bookstore", "book_store", "nha_sach", "nhà sách", "book-shop", "bookshop"}:
        label = "nhà sách"
    elif normalized_kind in {"book", "sach", "books"}:
        label = "sách"
    else:
        label = "địa điểm"
    query = f"{label} tại {normalized_location}" if normalized_location else label
    return f"https://www.google.com/maps/search/{quote_plus(query)}"


def build_maps_directions_url(origin: str, destination: str) -> str:
    origin_text = (origin or "").strip() or "vị trí của tôi"
    destination_text = (destination or "").strip()
    return f"https://www.google.com/maps/dir/{quote_plus(origin_text)}/{quote_plus(destination_text)}"


def _build_place_maps_url(title: str, address: str) -> str:
    destination = ", ".join(part for part in (title.strip(), address.strip()) if part)
    return f"https://www.google.com/maps/search/{quote_plus(destination or 'địa điểm')}"


def _api_key() -> str:
    load_dotenv(BASE_DIR / ".env")
    return os.getenv("SERPAPI_API_KEY", "").strip()


def _number(value: Any, default: float | int = 0) -> float | int:
    try:
        return float(value) if value is not None and value != "" else default
    except (TypeError, ValueError):
        return default


def _link_value(links: Any, *names: str) -> str:
    if not isinstance(links, dict):
        return ""
    for name in names:
        value = links.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_local_result(result: dict[str, Any], kind: str, location: str) -> dict[str, Any]:
    """Normalize one SerpApi local result to the stable schema used by Streamlit."""
    coordinates = result.get("gps_coordinates") or {}
    latitude = _number(coordinates.get("latitude"), None)
    longitude = _number(coordinates.get("longitude"), None)
    title = str(result.get("title") or result.get("name") or "Địa điểm chưa rõ").strip()
    address = str(result.get("address") or "").strip()
    links = result.get("links") or {}
    maps_url = _link_value(links, "directions", "maps", "place") or _build_place_maps_url(title, address)
    directions_url = _link_value(links, "directions") or build_maps_directions_url("", f"{title}, {address}")
    return {
        "title": title,
        "name": title,
        "address": address,
        "rating": _number(result.get("rating"), 0),
        "reviews": int(_number(result.get("reviews"), 0)),
        "type": str(result.get("type") or "").strip(),
        "types": result.get("types") if isinstance(result.get("types"), list) else [],
        "open_state": str(result.get("open_state") or "").strip(),
        "hours": str(result.get("hours") or "").strip(),
        "phone": str(result.get("phone") or "").strip(),
        "website": str(result.get("website") or "").strip(),
        "description": str(result.get("description") or "").strip(),
        "latitude": latitude,
        "longitude": longitude,
        "place_id": str(result.get("place_id") or "").strip(),
        "data_id": str(result.get("data_id") or "").strip(),
        "thumbnail": str(result.get("thumbnail") or "").strip(),
        "directions_url": directions_url,
        "google_maps_url": maps_url,
    }


def _search_locations(kind: str, location: str, limit: int = 10) -> list[dict[str, Any]]:
    api_key = _api_key()
    if not api_key:
        raise LocationServiceError("Thiếu SERPAPI_API_KEY trong file .env.")
    normalized_location = str(location or "").strip()
    label = "thư viện" if kind == "library" else "nhà sách"
    query = f"{label} tại {normalized_location}" if normalized_location else label
    try:
        response = requests.get(
            SERPAPI_URL,
            params={"engine": "google_maps", "type": "search", "q": query, "api_key": api_key, "hl": "vi", "gl": "vn"},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout as error:
        raise LocationServiceError("SerpApi hết thời gian chờ. Vui lòng thử lại sau.") from error
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "không xác định"
        raise LocationServiceError(f"SerpApi trả về lỗi HTTP {status_code}.") from error
    except requests.RequestException as error:
        raise LocationServiceError("Không thể kết nối đến SerpApi.") from error
    try:
        payload = response.json()
    except ValueError as error:
        raise LocationServiceError("SerpApi trả về dữ liệu không hợp lệ.") from error
    if not isinstance(payload, dict):
        raise LocationServiceError("SerpApi trả về dữ liệu không hợp lệ.")
    if payload.get("error"):
        raise LocationServiceError(f"SerpApi trả về lỗi: {payload['error']}")
    local_results = payload.get("local_results")
    if not isinstance(local_results, list) or not local_results:
        place_result = payload.get("place_results")
        if isinstance(place_result, dict) and place_result:
            local_results = [place_result]
    if not isinstance(local_results, list) or not local_results:
        raise LocationServiceError("Không tìm thấy địa điểm phù hợp.")
    safe_limit = max(1, min(int(limit), 50))
    return [normalize_local_result(item, kind, normalized_location) for item in local_results[:safe_limit] if isinstance(item, dict)]


def search_bookstores(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return _search_locations("bookstore", location, limit)


def search_libraries(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return _search_locations("library", location, limit)


def search_nearby_bookstores(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_bookstores(location, limit)


def search_nearby_libraries(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_libraries(location, limit)


def find_nearby_libraries(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_nearby_libraries(location, limit)


def find_nearby_bookstores(location: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_nearby_bookstores(location, limit)
