import logging

from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPError, HTTPStatusError

from app.models.schemas import (
    BufferRequest,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    IsochroneRequest,
    PointRequest,
)
from app.services import spatial_service
from app.services.external_api import (
    ExternalAPIClient,
    get_external_api_client,
    get_isochrone_api_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spatial", tags=["spatial"])


@router.get("/sample", response_model=GeoJSONFeatureCollection)
def get_sample_features() -> dict:
    """A small sample GeoJSON FeatureCollection, handy for the frontend map demo."""
    return spatial_service.sample_feature_collection()


@router.post("/poi", response_model=GeoJSONFeature)
async def get_poi(
        request: PointRequest,
        client: ExternalAPIClient = Depends(get_external_api_client),
) -> dict:
    """Return a chosen lat/lon point as a GeoJSON Point Feature, with no buffering.

    Enriches the point's properties with a name and address via reverse
    geocoding against the configured third-party API (OSM Nominatim's
    /reverse by default). If the lookup fails or the coordinates can't be
    resolved, the point is still returned — just without name/address.
    """
    feature = spatial_service.get_poi(
        lat=request.latitude,
        long=request.longitude,
    )

    try:
        reverse_result = await client.reverse_geocode(request.latitude, request.longitude)
        if not isinstance(reverse_result, dict) or "error" in reverse_result:
            # Nominatim responds 200 with an "error" key (rather than an HTTP
            # error status) when coordinates can't be resolved to a place.
            reverse_result = {}
    except Exception as exc:
        # Reverse geocoding is a best-effort enrichment step — the point
        # itself should always be returned even if the third-party lookup
        # fails for any reason (network error, timeout, unexpected/invalid
        # response body, rate limiting, etc.), so this deliberately catches
        # broadly rather than just httpx.HTTPError.
        logger.warning(
            "Reverse geocode failed for (%s, %s): %s", request.latitude, request.longitude, exc
        )
        reverse_result = {}

    address_details = reverse_result.get("address", {})
    display_name = reverse_result.get("display_name", {})
    feature["properties"].update(
        {
            "name": reverse_result.get("name") or None,
            "address": reverse_result.get("display_name"),
            "address_details": address_details or None,
            "display_name": display_name or None,
        }
    )

    return feature


@router.post("/buffer", response_model=GeoJSONFeature)
def buffer_point(request: BufferRequest) -> dict:
    """Buffer a lat/lon point by a distance in meters, returning a GeoJSON polygon."""
    return spatial_service.buffer_point(
        latitude=request.latitude,
        longitude=request.longitude,
        distance_meters=request.distance_meters,
    )


@router.post("/isochrone", response_model=GeoJSONFeatureCollection)
async def get_isochrone(
        request: IsochroneRequest,
        client: ExternalAPIClient = Depends(get_isochrone_api_client),
) -> dict:
    """Return an isochrone (reachable-area polygon) around a point, via the
    configured isochrone provider (Geoapify's Isoline API by default).

    Unlike /spatial/poi's reverse-geocode enrichment, the isochrone *is*
    the requested payload here rather than a nice-to-have addition — so
    failures are surfaced as proper error responses rather than degraded
    silently.
    """
    try:
        result = await client.get_isochrone(
            latitude=request.latitude,
            longitude=request.longitude,
            mode=request.mode,
            range_seconds=request.range_minutes * 60,
        )
    except HTTPStatusError as exc:
        logger.warning(
            "Isochrone failed for (%s, %s): %s", request.latitude, request.longitude, exc
        )
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
    except HTTPError as exc:
        # Network-level failures (timeout, connection refused, DNS, etc.)
        logger.warning(
            "Isochrone failed for (%s, %s): %s", request.latitude, request.longitude, exc
        )
        raise HTTPException(
            status_code=502, detail=f"Upstream isochrone request failed: {exc}"
        ) from exc
    except (ValueError, TimeoutError) as exc:
        # e.g. an invalid/unparseable response, or the async-computation
        # polling loop in get_isochrone() never resolved in time
        logger.warning(
            "Isochrone failed for (%s, %s): %s", request.latitude, request.longitude, exc
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return result

