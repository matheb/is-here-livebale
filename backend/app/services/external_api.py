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
        if self._settings.external_api_key:
            headers["Authorization"] = f"Bearer {self._settings.external_api_key}"

        async with httpx.AsyncClient(
            base_url=self._settings.external_api_base_url,
            timeout=self._settings.external_api_timeout_seconds,
            headers=headers,
        ) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    async def geocode(self, query: str) -> list[dict[str, Any]]:
        """Example call against OpenStreetMap Nominatim (the default configured API)."""
        return await self.get(
            "/search",
            params={"q": query, "format": "jsonv2", "limit": 5},
        )
    async def reverse_geocode(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Reverse-geocode a lat/lon into a name/address via the configured API
        (OSM Nominatim's /reverse by default).
        """
        return await self.get(
            "/reverse",
            params={"lat": latitude, "lon": longitude, "format": "jsonv2"},
        )


def get_external_api_client() -> ExternalAPIClient:
    """FastAPI dependency factory."""
    return ExternalAPIClient()
