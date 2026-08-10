"""Spatial data helpers built on shapely / geopandas.

Keeping the geospatial logic in a service module (rather than inline in
route handlers) makes it independently unit-testable and reusable.
"""
from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point, mapping, shape

# Geographic CRS (lat/lon) used for input/output GeoJSON.
WGS84 = "EPSG:4326"
# A metric, equal-area-ish projection good for short-range buffering in meters.
WEB_MERCATOR = "EPSG:3857"


def buffer_point(latitude: float, longitude: float, distance_meters: float) -> dict:
    """Buffer a WGS84 point by a distance in meters and return a GeoJSON polygon.

    The point is reprojected to a metric CRS to buffer accurately, then
    reprojected back to WGS84 for the response.
    """
    point_gdf = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(longitude, latitude)], crs=WGS84
    )
    buffered = point_gdf.to_crs(WEB_MERCATOR).buffer(distance_meters).to_crs(WGS84)
    geometry = mapping(buffered.iloc[0])
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "source_latitude": latitude,
            "source_longitude": longitude,
            "buffer_distance_meters": distance_meters,
        },
    }


def poi_point(latitude: float, longitude: float) -> dict:
    """Return a single point of interest as a plain GeoJSON Point Feature.

    Unlike buffer_point, this does no buffering/reprojection — it's the
    chosen point itself, validated and normalized into GeoJSON. Kept as a
    GeoDataFrame round-trip (rather than a bare dict) so validation and any
    future enrichment — e.g. reverse-geocoding via ExternalAPIClient, or
    spatial joins against a POI layer — stay consistent with the rest of
    this module.
    """
    point_gdf = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(longitude, latitude)], crs=WGS84
    )
    geometry = mapping(point_gdf.geometry.iloc[0])
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "latitude": latitude,
            "longitude": longitude,
        },
    }


def sample_feature_collection() -> dict:
    """Return a small sample GeoJSON FeatureCollection for frontend map demos."""
    cities = gpd.GeoDataFrame(
        {
            "name": ["Graz", "Vienna", "Redlands"],
            "geometry": [
                Point(15.4395, 47.0707),
                Point(16.3738, 48.2082),
                Point(-117.1825, 34.0556),
            ],
        },
        crs=WGS84,
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": {"name": row["name"]},
            }
            for _, row in cities.iterrows()
        ],
    }


def bbox_of_geometry(geometry: dict) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) bounds for a GeoJSON geometry —
    the order Overpass's bbox filter expects. Accepts any GeoJSON geometry
    dict (Polygon, MultiPolygon, etc.), e.g. an isochrone or buffer result.
    """
    geom = shape(geometry)
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    return (min_lat, min_lon, max_lat, max_lon)


def filter_features_within_geometry(geometry: dict, features: list[dict]) -> list[dict]:
    """Keep only GeoJSON Point Features that actually fall within the given
    GeoJSON polygon — not just its bounding box.

    Used to refine bbox-queried results (e.g. from Overpass, which doesn't
    reliably support true polygon filtering for ways/relations) down to
    the real isochrone/buffer shape.
    """
    geom = shape(geometry)
    return [
        feature
        for feature in features
        if geom.contains(Point(*feature["geometry"]["coordinates"]))
    ]

