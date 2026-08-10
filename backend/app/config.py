"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    # DEBUG shows every outgoing third-party request (with the API key
    # redacted); INFO shows successful calls + timing; WARNING shows only
    # failures. See app/logging_config.py.
    log_level: str = "INFO"

    external_api_base_url: str = "https://nominatim.openstreetmap.org"
    external_api_key: str = ""
    # Most REST APIs expect the key as a Bearer token (the default). Some
    # geocoders instead expect it as a query string parameter — e.g.
    # LocationIQ/Geoapify/OpenCage use `?key=...`. If set, the key is sent
    # as a query param under this name instead of an Authorization header.
    external_api_key_param_name: str = ""
    external_api_timeout_seconds: float = 10.0
    # OSM Nominatim's usage policy requires a descriptive User-Agent
    # identifying the application; requests without one (or with a generic
    # library default) are liable to be blocked. Set this to something that
    # identifies your app if you're using Nominatim, or any value your
    # configured third-party API expects.

    external_api_user_agent: str = "is_liveable_here_backend/0.1 (boglarka298@gmail.com)"

    # Isochrone provider (reachable-area polygons) — a separate service from
    # the geocoding provider above, since they're commonly different vendors.
    # Defaults to Geoapify's Isoline API (free tier: 3,000 credits/day).
    isochrone_api_base_url: str = "https://api.geoapify.com/v1"
    isochrone_api_key: str = ""
    isochrone_api_key_param_name: str = "apiKey"
    isochrone_api_timeout_seconds: float = 15.0

    # OSM/Overpass provider (amenities: shops, doctors, schools, restaurants
    # etc.) — free, no API key needed. Overpass queries can be slow for
    # larger areas, hence the longer default timeout.
    overpass_api_base_url: str = "https://overpass-api.de/api"
    overpass_api_timeout_seconds: float = 30.0




    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
