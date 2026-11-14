from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class LocationSearchRequest(BaseModel):
    location: str = Field("Hồ Chí Minh", description="City or district location to search nearby")
    kind: str = Field("all", description="bookstore, library, or all")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")


class LocationItem(BaseModel):
    title: str = ""
    address: str = ""
    phone: str = ""
    rating: Any = 0
    reviews_count: Any = 0
    maps_url: str = ""
    directions_url: str = ""
    kind: str = ""


class LocationSearchResponse(BaseModel):
    location: str = ""
    city: str = ""
    kind: str = "all"
    total: int = 0
    results: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    fallback_urls: dict[str, str] = {}

