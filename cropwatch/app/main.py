"""FastAPI app, CORS, and CropWatch HTTP routes."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.advice import get_advice
from app.config import get_settings
from app.diagnosis import DiagnosisError, diagnose_image
from app.risk import assess
from app.schemas import Crop, DiagnoseResponse, TreatmentLogRequest, TreatmentLogResponse
from app.storage import add_treatment, diagnosis_exists, init_db, list_diagnoses, save_diagnosis
from app.utils import compress_image, validate_image
from app.weather import WeatherError, fetch_weather

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CONFIDENCE_THRESHOLD = 0.6
EMPTY_WEATHER = {"avg_temp_c": 0.0, "avg_humidity_pct": 0.0, "total_rain_mm": 0.0}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize the SQLite schema when the API process starts."""
    init_db(get_settings().database_path)
    yield


app = FastAPI(title="CropWatch", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DiagnosisError)
async def handle_diagnosis_error(_request: object, exc: DiagnosisError) -> JSONResponse:
    """Turn diagnosis failures into a friendly HTTP 502."""
    logger.error("Diagnosis error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={"detail": "Diagnosis is temporarily unavailable. Please try again."},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for the API process."""
    return {"status": "ok"}


async def _read_image(image: UploadFile) -> bytes:
    """Read, size-check, and validate an uploaded leaf photo."""
    settings = get_settings()
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    data = await image.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds {settings.max_upload_mb:g} MB limit.",
        )
    try:
        validate_image(data, image.content_type or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return data


def _select_advice(candidates: list[dict[str, object]]) -> tuple[dict[str, object], bool]:
    """Choose treatment advice, using expert referral when confidence is low."""
    top_confidence = (
        float(candidates[0]["confidence"]) if candidates else 0.0  # type: ignore[arg-type]
    )
    low_confidence = (not candidates) or top_confidence < CONFIDENCE_THRESHOLD
    disease = str(candidates[0]["disease"]) if candidates else "unknown"
    return get_advice(disease, low_confidence), low_confidence


def _select_risk(
    candidates: list[dict[str, object]],
    daily_records: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Assess weather risk for the first candidate that has a usable score."""
    if not candidates:
        return assess({"disease": "unknown", "confidence": 0.0}, daily_records)
    return assess(candidates[0], daily_records)


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    image: Annotated[UploadFile, File()],
    crop: Annotated[Crop, Form()],
    latitude: Annotated[float, Form(ge=-90, le=90)],
    longitude: Annotated[float, Form(ge=-180, le=180)],
    symptoms: Annotated[str | None, Form()] = None,
    plants_affected_percent: Annotated[int | None, Form(ge=0, le=100)] = None,
) -> DiagnoseResponse:
    """Diagnose a leaf photo and attach weather risk plus treatment advice."""
    raw_bytes = await _read_image(image)
    compressed = compress_image(raw_bytes)
    candidates = await asyncio.to_thread(
        diagnose_image,
        compressed,
        crop.value,
        symptoms,
        plants_affected_percent,
    )
    daily_records: list[dict[str, object]] | None
    try:
        daily_records, weather_summary = await asyncio.to_thread(
            fetch_weather, latitude, longitude
        )
    except WeatherError as exc:
        logger.error("Weather fetch failed: %s", exc)
        daily_records = None
        weather_summary = dict(EMPTY_WEATHER)
    advice, _low = _select_advice(candidates)
    record = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "crop": crop.value,
        "candidates": candidates,
        "risk": _select_risk(candidates, daily_records),
        "advice": advice,
        "weather_summary": weather_summary,
    }
    save_diagnosis(record)
    return DiagnoseResponse.model_validate(record)


@app.get("/history")
def history(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict[str, object]:
    """Return the most recent saved diagnoses."""
    return {"items": list_diagnoses(limit=limit)}


@app.post("/treatment-log", response_model=TreatmentLogResponse)
def treatment_log(body: TreatmentLogRequest) -> TreatmentLogResponse:
    """Store a treatment entry linked to an existing diagnosis."""
    if not diagnosis_exists(body.diagnosis_id):
        raise HTTPException(status_code=404, detail="Diagnosis was not found.")
    saved = add_treatment(body.diagnosis_id, body.treatment, body.date)
    return TreatmentLogResponse.model_validate(saved)
