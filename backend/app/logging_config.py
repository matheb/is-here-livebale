"""Application-wide logging configuration.

Neither FastAPI nor uvicorn configures Python's root logger for you. Without
this, `logger.info(...)` / `logger.debug(...)` calls anywhere in the app are
silently dropped — Python's logging module falls back to a "last resort"
handler that only prints WARNING and above. Call configure_logging() once,
early, before the app starts handling requests (see app/main.py).
"""
import logging

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )