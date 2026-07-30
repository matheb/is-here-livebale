"""Pydantic request/response schemas."""
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    environment: str


class BufferRequest(BaseModel):
    """Request to buffer a point by a distance in meters."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    distance_meters: float = Field(..., gt=0, le=100_000)

class POIRequest(BaseModel):
    """Request identifying a POI, with no buffering."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]


class GeocodeResult(BaseModel):
    display_name: str
    latitude: float
    longitude: float
    raw: dict[str, Any] = Field(default_factory=dict)
