from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Query
from backend.schemas.location_schema import LocationSearchResponse
from location_service import (
    search_nearby_bookstores,
    search_nearby_libraries,
    build_google_maps_search_url,
)

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/search", response_model=LocationSearchResponse)
def search_locations(
    location: str = Query("Hồ Chí Minh", description="City or district location"),
    kind: str = Query("all", description="bookstore, library, or all"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
) -> LocationSearchResponse:
    results: list[dict[str, Any]] = []

    if kind in {"bookstore", "all"}:
        try:
            bs = search_nearby_bookstores(location=location, limit=limit)
            results.extend(bs)
        except Exception:
            pass

    if kind in {"library", "all"}:
        try:
            libs = search_nearby_libraries(location=location, limit=limit)
            results.extend(libs)
        except Exception:
            pass

    fallback_urls = {
        "google_maps_bookstores": build_google_maps_search_url("nhà sách", location),
        "google_maps_libraries": build_google_maps_search_url("thư viện", location),
    }

    return LocationSearchResponse(
        location=location,
        kind=kind,
        results=results[:limit],
        fallback_urls=fallback_urls,
    )

