from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import external, health, spatial
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Spatial API Backend",
        description="FastAPI backend for spatial data + third-party API integration",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(spatial.router)
    app.include_router(external.router)

    return app


app = create_app()
