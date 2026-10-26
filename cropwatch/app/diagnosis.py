"""Gemini-based leaf disease diagnosis."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

CROP_DISEASES: dict[str, list[str]] = {
    "tomato": [
        "Early blight",
        "Late blight",
        "Leaf mold",
        "Septoria leaf spot",
        "Healthy",
    ],
    "potato": ["Early blight", "Late blight", "Healthy"],
    "maize": ["Gray leaf spot", "Northern leaf blight", "Common rust", "Healthy"],
    "rice": ["Bacterial leaf blight", "Brown spot", "Leaf blast", "Healthy"],
}

TIMEOUT_MS = 30_000
MAX_CANDIDATES = 3


class DiagnosisError(Exception):
    """Raised when Gemini cannot return usable diagnosis JSON."""


def _client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=TIMEOUT_MS),
    )


def build_prompt(
    crop: str,
    symptoms: str | None = None,
    plants_affected_percent: int | None = None,
) -> str:
    """Build the text prompt that constrains Gemini's JSON output."""
    allowed = ", ".join(CROP_DISEASES[crop])
    extra = ""
    if symptoms:
        extra += f"\nObserved symptoms: {symptoms}."
    if plants_affected_percent is not None:
        extra += f"\nShare of plants that look affected: {plants_affected_percent}%."
    return (
        f"You identify crop diseases from a leaf or plant photo.\n"
        f"Crop: {crop}\n"
        f"You may only choose disease names from this list: {allowed}.\n"
        "If the image is not a plant leaf, or is too blurry to judge, "
        "return confidence values all below 0.3.\n"
        "Return ONLY valid JSON, with no markdown fences, in the form "
        '{"candidates": [{"disease": "...", "confidence": 0.0, '
        '"description": "..."}]}.\n'
        "Include up to 3 items sorted by confidence descending. "
        "Confidences must sum to at most 1.0."
        f"{extra}"
    )


def _call_gemini(image_bytes: bytes, prompt: str) -> str:
    settings = get_settings()
    try:
        response = _client().models.generate_content(
            model=settings.gemini_model,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=TIMEOUT_MS),
            ),
        )
    except Exception as exc:
        message = str(exc).lower()
        if "timeout" in message or "deadline" in message:
            logger.error("Gemini diagnosis timed out: %s", exc)
            raise DiagnosisError("Diagnosis timed out.") from exc
        logger.error("Gemini diagnosis failed: %s", exc)
        raise DiagnosisError("Diagnosis service failed.") from exc
    text = getattr(response, "text", None)
    if not text:
        raise DiagnosisError("Diagnosis service returned an empty response.")
    return text


def _parse_candidates(raw: str, crop: str) -> list[dict[str, Any]]:
    """Parse model JSON and keep only allowed disease names."""
    payload = json.loads(raw)
    items = payload.get("candidates")
    if not isinstance(items, list):
        raise ValueError("candidates is missing")
    allowed = set(CROP_DISEASES[crop])
    cleaned: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        disease = str(item.get("disease", "")).strip()
        if disease not in allowed:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        confidence = min(max(confidence, 0.0), 1.0)
        description = str(item.get("description", "")).strip()
        cleaned.append(
            {
                "disease": disease,
                "confidence": confidence,
                "description": description,
            }
        )
    cleaned.sort(key=lambda row: row["confidence"], reverse=True)
    return cleaned[:MAX_CANDIDATES]


def diagnose_image(
    image_bytes: bytes,
    crop: str,
    symptoms: str | None = None,
    plants_affected_percent: int | None = None,
) -> list[dict[str, Any]]:
    """Return up to three disease candidates for a compressed leaf photo."""
    if crop not in CROP_DISEASES:
        raise DiagnosisError("Unsupported crop.")
    prompt = build_prompt(crop, symptoms, plants_affected_percent)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            raw = _call_gemini(image_bytes, prompt)
            return _parse_candidates(raw, crop)
        except DiagnosisError:
            raise
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            last_error = exc
            logger.error("Gemini JSON parse failed (attempt %s): %s", attempt + 1, exc)
    raise DiagnosisError("Diagnosis result could not be read.") from last_error
