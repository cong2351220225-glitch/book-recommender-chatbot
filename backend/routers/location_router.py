from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Query, Body
from backend.schemas.location_schema import LocationSearchResponse, LocationSearchRequest
from location_service import (
    search_nearby_bookstores,
    search_nearby_libraries,
    build_google_maps_search_url,
)

router = APIRouter(prefix="/locations", tags=["Locations"])


def _execute_location_search(
    city: str | None = None,
    location: str | None = None,
    query: str | None = None,
    kind: str = "all",
    place_type: str | None = None,
    type_: str | None = None,
    limit: int = 10,
) -> LocationSearchResponse:
    # Resolve target location
    target_location = (city or location or query or "Đà Nẵng").strip()
    target_kind = (place_type or type_ or kind or "all").strip().lower()
    safe_limit = max(1, min(int(limit), 50))

    results: list[dict[str, Any]] = []

    if target_kind in {"bookstore", "all", "nhà sách", "nha sach"}:
        try:
            bs = search_nearby_bookstores(location=target_location, limit=safe_limit)
            results.extend(bs)
        except Exception:
            pass

    if target_kind in {"library", "all", "thư viện", "thu vien"}:
        try:
            libs = search_nearby_libraries(location=target_location, limit=safe_limit)
            results.extend(libs)
        except Exception:
            pass

    # Ensure every location item has both name and title, maps_url, opening_hours, kind
    for loc in results:
        title = loc.get("title") or loc.get("name") or "Địa điểm"
        loc["title"] = title
        loc["name"] = title
        if not loc.get("opening_hours"):
            loc["opening_hours"] = loc.get("hours") or "08:00 - 22:00"
        if not loc.get("hours"):
            loc["hours"] = loc.get("opening_hours")
        if not loc.get("maps_url"):
            loc["maps_url"] = loc.get("google_maps_url") or f"https://www.google.com/maps/search/?api=1&query={title}"
        if not loc.get("google_maps_url"):
            loc["google_maps_url"] = loc.get("maps_url")
        if not loc.get("kind"):
            loc["kind"] = loc.get("type") or target_kind

    limited_results = results[:safe_limit]

    fallback_urls = {
        "google_maps_bookstores": build_google_maps_search_url("nhà sách", target_location),
        "google_maps_libraries": build_google_maps_search_url("thư viện", target_location),
    }

    return LocationSearchResponse(
        location=target_location,
        city=target_location,
        kind=target_kind,
        total=len(limited_results),
        results=limited_results,
        locations=limited_results,
        fallback_urls=fallback_urls,
    )


@router.get("", response_model=LocationSearchResponse)
@router.get("/", response_model=LocationSearchResponse)
def get_locations(
    city: str | None = Query(None, description="Tên thành phố hoặc quận/huyện"),
    location: str | None = Query(None, description="Địa điểm cần tìm"),
    query: str | None = Query(None, description="Từ khóa địa điểm"),
    kind: str = Query("all", description="bookstore, library, hoặc all"),
    place_type: str | None = Query(None, description="Alias cho kind"),
    type: str | None = Query(None, description="Alias cho kind"),
    limit: int = Query(10, ge=1, le=50, description="Số lượng kết quả tối đa"),
) -> LocationSearchResponse:
    return _execute_location_search(
        city=city,
        location=location,
        query=query,
        kind=kind,
        place_type=place_type,
        type_=type,
        limit=limit,
    )


@router.get("/search", response_model=LocationSearchResponse)
def search_locations_get(
    city: str | None = Query(None, description="Tên thành phố"),
    location: str | None = Query(None, description="City or district location"),
    query: str | None = Query(None, description="Từ khóa địa điểm"),
    kind: str = Query("all", description="bookstore, library, or all"),
    place_type: str | None = Query(None, description="Alias cho kind"),
    type: str | None = Query(None, description="Alias cho kind"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
) -> LocationSearchResponse:
    return _execute_location_search(
        city=city,
        location=location,
        query=query,
        kind=kind,
        place_type=place_type,
        type_=type,
        limit=limit,
    )


@router.post("/search", response_model=LocationSearchResponse)
def search_locations_post(
    req: LocationSearchRequest = Body(...),
) -> LocationSearchResponse:
    return _execute_location_search(
        location=req.location,
        kind=req.kind,
        limit=req.limit,
    )


