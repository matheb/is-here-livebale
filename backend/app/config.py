"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

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


    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
