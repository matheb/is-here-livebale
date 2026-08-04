import logging

from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPError, HTTPStatusError

from app.models.schemas import GeocodeResult
from app.services.external_api import ExternalAPIClient, get_external_api_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external", tags=["external"])


@router.get("/geocode", response_model=list[GeocodeResult])
async def geocode(
        q: str,
        client: ExternalAPIClient = Depends(get_external_api_client),
) -> list[GeocodeResult]:
    """Proxy a geocoding lookup to the configured third-party API (OSM Nominatim
    by default; point EXTERNAL_API_BASE_URL at any other geocoder if needed).
    """
    try:
        results = await client.geocode(q)
    except HTTPStatusError as exc:
        logger.warning("Geocode failed for query %r: %s", q, exc)
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
    except HTTPError as exc:
        # Network-level failures (timeout, connection refused, DNS, etc.)
        logger.warning("Geocode failed for query %r: %s", q, exc)
        raise HTTPException(
            status_code=502, detail=f"Upstream geocoding request failed: {exc}"
        ) from exc
    except ValueError as exc:
        # e.g. the upstream response body wasn't valid JSON
        logger.warning("Geocode failed for query %r: %s", q, exc)
        raise HTTPException(
            status_code=502, detail="Upstream geocoding service returned an invalid response"
        ) from exc

    return [
        GeocodeResult(
            display_name=item.get("display_name", ""),
            latitude=float(item["lat"]),
            longitude=float(item["lon"]),
            raw=item,
        )
        for item in results
    ]
