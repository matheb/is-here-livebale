"""Thin async client for calling a configured third-party API.

Centralizing the httpx client here means routes stay simple, timeouts /
headers / base URLs are configured in one place, and the client is easy
to mock in tests (see tests/test_external.py).
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings


class ExternalAPIClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

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

        print(f"request_params-------- {request_params}")
        async with httpx.AsyncClient(
            base_url=self._settings.external_api_base_url,
            timeout=self._settings.external_api_timeout_seconds,
            headers=headers,
        ) as client:
            response = await client.get(path, params=request_params)
            response.raise_for_status()
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
