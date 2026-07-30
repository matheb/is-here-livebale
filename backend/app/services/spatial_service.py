"""Spatial data helpers built on shapely / geopandas.

Keeping the geospatial logic in a service module (rather than inline in
route handlers) makes it independently unit-testable and reusable.
"""
from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point, mapping

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


def sample_feature_collection() -> dict:
    """Return a small sample GeoJSON FeatureCollection for frontend map demos."""
    cities = gpd.GeoDataFrame(
        {
            # "name": ["Graz", "Vienna", "Redlands"],
            "name": ["Graz"],
            "geometry": [
                Point(15.4395, 47.0707),
                # Point(16.3738, 48.2082),
                # Point(-117.1825, 34.0556),
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

def get_poi(lat: float, long: float) -> dict:
    """Return a GeoJSON FeatureCollection based on a selected POI on the map"""
    poi_gdf = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(long, lat)], crs=WGS84
    )
    # geometry = poi_gdf.geometry
    geometry = mapping(poi_gdf[0])
    print(geometry)

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "source_latitude": lat,
            "source_longitude": long,
            "id": f"{lat}-{long}"
        },
    }
