"""Thin async client for calling configured third-party APIs.

Centralizing the httpx client here means routes stay simple, timeouts /
headers / base URLs are configured in one place, and the client is easy
to mock in tests (see tests/test_external.py). Supports three independent
provider configs (geocoding, isochrone, osm), since those are commonly
different vendors — see Settings.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

Provider = Literal["geocoding", "isochrone", "osm"]

# Geoapify's Isoline API computes some isochrones asynchronously: a 202
# response means "still computing," and the result must be polled for
# using the id it returns. See get_isochrone().
_ASYNC_PENDING_STATUS = 202


class ExternalAPIClient:
    def __init__(self, settings: Settings | None = None, provider: Provider = "geocoding") -> None:
        self._settings = settings or get_settings()
        self._provider = provider

    @property
    def _base_url(self) -> str:
        if self._provider == "isochrone":
            return self._settings.isochrone_api_base_url
        if self._provider == "osm":
            return self._settings.overpass_api_base_url
        return self._settings.external_api_base_url

    @property
    def _api_key(self) -> str:
        # Overpass needs no authentication — explicit branch (rather than
        # falling through to the geocoding provider's key) so an OSM
        # request can never accidentally pick up an unrelated API key.
        if self._provider == "osm":
            return ""
        if self._provider == "isochrone":
            return self._settings.isochrone_api_key
        return self._settings.external_api_key

    @property
    def _key_param_name(self) -> str:
        if self._provider == "osm":
            return ""
        if self._provider == "isochrone":
            return self._settings.isochrone_api_key_param_name
        return self._settings.external_api_key_param_name

    @property
    def _timeout_seconds(self) -> float:
        if self._provider == "isochrone":
            return self._settings.isochrone_api_timeout_seconds
        if self._provider == "osm":
            return self._settings.overpass_api_timeout_seconds
        return self._settings.external_api_timeout_seconds

    def _redact_url(self, url: str) -> str:
        """Mask the API key in a fully-built request URL before logging it."""
        key_param = self._key_param_name
        if not key_param:
            return url
        parts = urlsplit(url)
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        redacted_pairs = [
            (k, "***redacted***" if k == key_param else v) for k, v in query_pairs
        ]
        redacted_query = urlencode(redacted_pairs)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted_query, parts.fragment))

    def _redact_headers(self, headers: httpx.Headers) -> dict[str, str]:
        """Mask any Authorization header before logging it."""
        return {
            name: ("***redacted***" if name.lower() == "authorization" else value)
            for name, value in headers.items()
        }

    def _build_headers(self) -> dict[str, str]:
        headers = {"User-Agent": self._settings.external_api_user_agent}
        if self._api_key and not self._key_param_name:
            # Default: Authorization: Bearer <key>
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _send_and_log(
        self, client: httpx.AsyncClient, request: httpx.Request, body_preview: str | None = None
    ) -> httpx.Response:
        """Shared send/log/error-handling logic for both GET (_send) and
        POST (_send_post) requests; returns the raw response (not .json())
        so callers needing the status code — e.g. get_isochrone(), to
        detect Geoapify's async 202 — can inspect it directly.
        """
        redacted_url = self._redact_url(str(request.url))

        logger.debug(
            "External API request: %s %s headers=%s%s",
            request.method, redacted_url, self._redact_headers(request.headers),
            f" body={body_preview[:500]!r}" if body_preview else "",
        )

        start = time.monotonic()
        try:
            response = await client.send(request)
        except httpx.HTTPError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(
                "External API request failed: %s %s (%.0fms): %s",
                request.method, redacted_url, elapsed_ms, exc,
            )
            raise

        elapsed_ms = (time.monotonic() - start) * 1000

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # The default httpx message is just the status line (e.g.
            # "400 Bad Request") — the response body usually contains
            # the actual reason (invalid key, bad param, quota, etc.),
            # which is essential for diagnosing third-party API errors.
            body = response.text[:500]
            logger.warning(
                "External API returned %s for %s %s (%.0fms). Response body: %s",
                response.status_code, request.method, redacted_url, elapsed_ms, body,
            )
            raise httpx.HTTPStatusError(
                f"{exc}. Response body: {body!r}",
                request=exc.request,
                response=exc.response,
            ) from exc

        logger.info(
            "External API request succeeded: %s %s -> %s (%.0fms)",
            request.method, redacted_url, response.status_code, elapsed_ms,
        )
        return response

    async def _send(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Build, log, and send a GET request; return the raw response."""
        headers = self._build_headers()
        request_params = dict(params or {})

        if self._api_key and self._key_param_name:
            # e.g. LocationIQ/Geoapify/OpenCage: key goes in the query string
            request_params[self._key_param_name] = self._api_key

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers=headers,
        ) as client:
            # Build the request explicitly (rather than calling client.get()
            # directly) so we can log the *actual* request httpx will send —
            # the real, fully percent-encoded URL and headers — instead of
            # reconstructing an approximation from the base URL/path/params
            # ourselves, which can drift from what's really on the wire.
            request = client.build_request("GET", path, params=request_params)
            return await self._send_and_log(client, request)

    async def _send_post(self, path: str, data: dict[str, Any] | str) -> httpx.Response:
        """Build, log, and send a POST request (form-encoded body); return
        the raw response. Used for APIs like Overpass that take a request
        body rather than query params — GET wouldn't reliably work there
        given how long an Overpass query string can get.
        """
        headers = self._build_headers()

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers=headers,
        ) as client:
            request = client.build_request("POST", path, data=data)
            body_preview = data if isinstance(data, str) else str(data)
            return await self._send_and_log(client, request, body_preview=body_preview)

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._send(path, params)
        return response.json()

    async def geocode(self, query: str) -> list[dict[str, Any]]:
        """Example call against OpenStreetMap Nominatim (the default configured API)."""
        return await self.get(
            "/search",
            params={"q": query, "format": "json", "limit": 5},
        )

    async def reverse_geocode(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Reverse-geocode a lat/lon into a name/address via the configured API
        (OSM Nominatim's /reverse by default).
        """
        return await self.get(
            "/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                # Without this, the structured "address" breakdown (city,
                # road, country, etc.) isn't included in the response at all
                # — only display_name is returned by default.
                "addressdetails": 1,
            },
        )

    async def get_isochrone(
        self,
        latitude: float,
        longitude: float,
        mode: str,
        range_seconds: int,
        max_poll_attempts: int = 10,
        poll_interval_seconds: float = 2.0,
    ) -> dict[str, Any]:
        """Fetch an isochrone (reachable-area polygon) around a point, via
        the configured isochrone provider (Geoapify's Isoline API by
        default). Returns a GeoJSON FeatureCollection.

        Geoapify computes some isolines asynchronously — a 202 response
        means the result isn't ready yet and must be polled for using the
        id it returns. This handles that transparently: callers always get
        back the final result, or an exception if it never completes.
        """
        response = await self._send(
            "/isoline",
            params={
                "lat": latitude,
                "lon": longitude,
                "type": "time",
                "mode": mode,
                "range": range_seconds,
            },
        )

        if response.status_code != _ASYNC_PENDING_STATUS:
            return response.json()

        pending = response.json()
        isoline_id = pending.get("properties", {}).get("id")
        if not isoline_id:
            raise ValueError(
                "Isochrone provider returned 202 (pending) but no id to poll for"
            )

        logger.info("Isochrone computation pending (id=%s); polling for result", isoline_id)

        for _attempt in range(max_poll_attempts):
            await asyncio.sleep(poll_interval_seconds)
            poll_response = await self._send("/isoline", params={"id": isoline_id})
            if poll_response.status_code != _ASYNC_PENDING_STATUS:
                return poll_response.json()

        total_wait = max_poll_attempts * poll_interval_seconds
        raise TimeoutError(
            f"Isochrone (id={isoline_id}) did not complete after {total_wait:.0f}s of polling"
        )

    async def query_overpass(self, query: str) -> dict[str, Any]:
        """Run a raw Overpass QL query against the configured OSM/Overpass
        endpoint (overpass-api.de by default). Returns the parsed JSON
        body — a dict with an "elements" list.
        """
        response = await self._send_post("/interpreter", data={"data": query})
        return response.json()


def get_external_api_client() -> ExternalAPIClient:
    """FastAPI dependency factory for the geocoding provider."""
    return ExternalAPIClient(provider="geocoding")


def get_isochrone_api_client() -> ExternalAPIClient:
    """FastAPI dependency factory for the isochrone provider."""
    return ExternalAPIClient(provider="isochrone")


def get_osm_api_client() -> ExternalAPIClient:
    """FastAPI dependency factory for the OSM/Overpass provider."""
    return ExternalAPIClient(provider="osm")
