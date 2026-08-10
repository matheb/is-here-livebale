"""OSM/Overpass integration: build category queries, parse results into
categorized GeoJSON features.

Kept separate from external_api.py (which only knows how to send an HTTP
request and get JSON back) and spatial_service.py (general geometry ops) —
this module is specifically about Overpass QL syntax and OSM tag semantics.
"""
from __future__ import annotations

from typing import Any, Literal

Category = Literal["shops", "doctors", "schools", "restaurants"]

ALL_CATEGORIES: list[Category] = ["shops", "doctors", "schools", "restaurants"]

# Each category maps to one or more OSM tag filters (Overpass QL syntax).
# Doctors specifically have two overlapping tagging conventions in OSM (the
# older `amenity` scheme and the newer `healthcare` scheme) — both are
# queried to catch more real-world data.
_CATEGORY_TAG_FILTERS: dict[Category, list[str]] = {
    "shops": ['["shop"]'],
    "doctors": ['["amenity"="doctors"]', '["healthcare"="doctor"]'],
    "schools": ['["amenity"="school"]'],
    "restaurants": [
        '["amenity"="restaurant"]',
        '["amenity"="cafe"]',
        '["amenity"="fast_food"]',
    ],
}


def build_overpass_query(
    categories: list[Category],
    bbox: tuple[float, float, float, float],
    timeout_seconds: int = 25,
) -> str:
    """Build an Overpass QL query for the given categories within a bbox.

    `bbox` is (south, west, north, east) — degrees, matching Overpass's own
    bbox filter order (not the (west, south, east, north) order some other
    tools use).

    Uses a bounding box rather than Overpass's `poly` filter: `poly` is
    only reliably supported for nodes, whereas bbox works uniformly for
    nodes/ways/relations (shops/schools/etc. are frequently mapped as
    building outlines, not just points). The precise polygon shape is
    applied afterward, server-side, via
    spatial_service.filter_features_within_geometry() — Overpass here is
    just a coarse pre-filter.
    """
    south, west, north, east = bbox
    bbox_str = f"{south},{west},{north},{east}"

    clauses = [
        f"  nwr{tag_filter}({bbox_str});"
        for category in categories
        for tag_filter in _CATEGORY_TAG_FILTERS.get(category, [])
    ]

    return (
        f"[out:json][timeout:{timeout_seconds}];\n"
        f"(\n" + "\n".join(clauses) + "\n);\n"
        f"out center tags;"
    )


def _category_for_tags(tags: dict[str, str]) -> Category | None:
    """Reverse-map an OSM element's tags back to one of our categories."""
    if "shop" in tags:
        return "shops"

    amenity = tags.get("amenity")
    if tags.get("healthcare") == "doctor" or amenity == "doctors":
        return "doctors"
    if amenity == "school":
        return "schools"
    if amenity in ("restaurant", "cafe", "fast_food"):
        return "restaurants"

    return None


def elements_to_geojson_features(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw Overpass elements (nodes/ways/relations) into GeoJSON
    Point Features, each tagged with our category and a display name.

    Elements whose tags don't map to a known category are skipped (the
    bbox pre-filter can occasionally return neighboring tag combinations
    we didn't ask for).
    """
    features = []

    for element in elements:
        tags = element.get("tags", {})
        category = _category_for_tags(tags)
        if category is None:
            continue

        # Nodes have lat/lon directly on the element; ways/relations only
        # have a representative point under "center", present because the
        # query uses `out center`.
        if "lat" in element and "lon" in element:
            lat, lon = element["lat"], element["lon"]
        else:
            center = element.get("center")
            if not center:
                continue
            lat, lon = center["lat"], center["lon"]

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "category": category,
                    "name": tags.get("name"),
                    "osm_id": element.get("id"),
                    "osm_type": element.get("type"),
                    "tags": tags,
                },
            }
        )

    return features