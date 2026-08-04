"""Thin async client for calling a configured third-party API.

Centralizing the httpx client here means routes stay simple, timeouts /
headers / base URLs are configured in one place, and the client is easy
to mock in tests (see tests/test_external.py).
"""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ExternalAPIClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _redact_url(self, url: str) -> str:
        """Mask the API key in a fully-built request URL before logging it."""
        key_param = self._settings.external_api_key_param_name
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

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        headers = {"User-Agent": self._settings.external_api_user_agent}
        request_params = dict(params or {})

        if self._settings.external_api_key:
            if self._settings.external_api_key_param_name:
                # e.g. LocationIQ/Geoapify/OpenCage: key goes in the query string
                request_params[self._settings.external_api_key_param_name] = (
                    self._settings.external_api_key
                )
            else:
                # Default: Authorization: Bearer <key>
                headers["Authorization"] = f"Bearer {self._settings.external_api_key}"

        async with httpx.AsyncClient(
                base_url=self._settings.external_api_base_url,
                timeout=self._settings.external_api_timeout_seconds,
                headers=headers,
        ) as client:
            # Build the request explicitly (rather than calling client.get()
            # directly) so we can log the *actual* request httpx will send —
            # the real, fully percent-encoded URL and headers — instead of
            # reconstructing an approximation from the base URL/path/params
            # ourselves, which can drift from what's really on the wire.
            request = client.build_request("GET", path, params=request_params)
            redacted_url = self._redact_url(str(request.url))

            logger.debug(
                "External API request: %s %s headers=%s",
                request.method, redacted_url, self._redact_headers(request.headers),
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
                body_preview = response.text[:500]
                logger.warning(
                    "External API returned %s for %s %s (%.0fms). Response body: %s",
                    response.status_code, request.method, redacted_url, elapsed_ms, body_preview,
                )
                raise httpx.HTTPStatusError(
                    f"{exc}. Response body: {body_preview!r}",
                    request=exc.request,
                    response=exc.response,
                ) from exc

            logger.info(
                "External API request succeeded: %s %s -> %s (%.0fms)",
                request.method, redacted_url, response.status_code, elapsed_ms,
            )
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
            params={"lat": latitude, "lon": longitude, "format": "json"},
        )


def get_external_api_client() -> ExternalAPIClient:
    """FastAPI dependency factory."""
    return ExternalAPIClient()
