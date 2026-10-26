"""Load CropWatch settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FRONTEND_ORIGIN = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the CropWatch API."""

    gemini_api_key: str
    gemini_model: str
    allowed_origins: list[str]
    database_path: str
    max_upload_mb: float


def _parse_origins(raw: str | None) -> list[str]:
    """Return unique CORS origins, always including the local Vite app."""
    origins = [DEFAULT_FRONTEND_ORIGIN]
    if raw:
        for item in raw.split(","):
            origin = item.strip()
            if origin and origin not in origins:
                origins.append(origin)
    return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once. Raise if GEMINI_API_KEY is missing."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and set your key."
        )
    max_upload = os.getenv("MAX_UPLOAD_MB", "5").strip()
    try:
        max_upload_mb = float(max_upload)
    except ValueError as exc:
        raise RuntimeError("MAX_UPLOAD_MB must be a number.") from exc
    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash",
        allowed_origins=_parse_origins(os.getenv("ALLOWED_ORIGINS")),
        database_path=os.getenv("DATABASE_PATH", "cropwatch.db").strip()
        or "cropwatch.db",
        max_upload_mb=max_upload_mb,
    )
