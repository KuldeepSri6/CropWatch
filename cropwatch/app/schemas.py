"""Pydantic models for CropWatch request and response bodies."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Crop(str, Enum):
    """Supported crop types."""

    tomato = "tomato"
    potato = "potato"
    maize = "maize"
    rice = "rice"


class DiseaseCandidate(BaseModel):
    """A single disease prediction from the vision model."""

    disease: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str


class RiskResult(BaseModel):
    """Weather-driven risk for the top disease candidate."""

    level: Literal["low", "moderate", "high", "unknown"]
    favorable_days: int
    window_days: int
    reason: str


class AdviceResult(BaseModel):
    """Treatment guidance returned with a diagnosis."""

    message: str
    steps: list[str]
    low_confidence: bool
    expert_referral: str


class WeatherSummary(BaseModel):
    """Aggregated weather over the 12-day analysis window."""

    avg_temp_c: float
    avg_humidity_pct: float
    total_rain_mm: float


class DiagnoseResponse(BaseModel):
    """Full /diagnose response payload."""

    id: str
    created_at: str
    crop: str
    candidates: list[DiseaseCandidate]
    risk: RiskResult
    advice: AdviceResult
    weather_summary: WeatherSummary


class TreatmentLogRequest(BaseModel):
    """Body for POST /treatment-log."""

    diagnosis_id: str = Field(min_length=1)
    treatment: str = Field(min_length=1)
    date: str

    @field_validator("date")
    @classmethod
    def validate_iso_date(cls, value: str) -> str:
        """Require YYYY-MM-DD."""
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must be in YYYY-MM-DD format") from exc
        return value


class TreatmentLogResponse(BaseModel):
    """Confirmation that a treatment entry was stored."""

    id: str
    diagnosis_id: str
    treatment: str
    date: str


class HistoryResponse(BaseModel):
    """Recent diagnoses loaded from SQLite."""

    items: list[DiagnoseResponse]
