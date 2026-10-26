"""Pure weather-risk rules for CropWatch disease candidates."""

from __future__ import annotations

from typing import Any, Mapping

WINDOW_DAYS = 12

RULES: dict[str, dict[str, Any]] = {
    "Early blight": {
        "temp_min": 24.0,
        "temp_max": 29.0,
        "humidity_threshold": 90,
        "min_humidity_hours": 6,
        "min_precip_mm": None,
        "summary": (
            "mean temperature 24-29 C and humidity above 90% for at least 6 hours"
        ),
    },
    "Late blight": {
        "temp_min": 10.0,
        "temp_max": 24.0,
        "humidity_threshold": 90,
        "min_humidity_hours": 8,
        "min_precip_mm": None,
        "summary": (
            "mean temperature 10-24 C and humidity above 90% for at least 8 hours"
        ),
    },
    "Leaf mold": {
        "temp_min": 20.0,
        "temp_max": 25.0,
        "humidity_threshold": 85,
        "min_humidity_hours": 8,
        "min_precip_mm": None,
        "summary": (
            "mean temperature 20-25 C and humidity above 85% for at least 8 hours"
        ),
    },
    "Gray leaf spot": {
        "temp_min": 22.0,
        "temp_max": 30.0,
        "humidity_threshold": 85,
        "min_humidity_hours": 10,
        "min_precip_mm": None,
        "summary": (
            "mean temperature 22-30 C and humidity above 85% for at least 10 hours"
        ),
    },
    "Bacterial leaf blight": {
        "temp_min": 25.0,
        "temp_max": 34.0,
        "humidity_threshold": None,
        "min_humidity_hours": 0,
        "min_precip_mm": 5.0,
        "summary": (
            "mean temperature 25-34 C and more than 5 mm of precipitation"
        ),
    },
}


def _humidity_hours(day: Mapping[str, Any], threshold: int) -> int:
    """Return stored hour counts for the requested humidity threshold."""
    if threshold >= 90:
        return int(day.get("humidity_hours_above_90", 0))
    return int(day.get("humidity_hours_above_85", 0))


def is_favorable_day(day: Mapping[str, Any], rule: Mapping[str, Any]) -> bool:
    """Return True if a daily weather record meets a disease rule.

    Temperature bounds are inclusive. Humidity must be strictly above the
    rule threshold for the required number of hours. Precipitation, when
    used, must be strictly above the rule minimum.
    """
    mean_temp = float(day["mean_temp_c"])
    if mean_temp < float(rule["temp_min"]) or mean_temp > float(rule["temp_max"]):
        return False
    min_precip = rule.get("min_precip_mm")
    if min_precip is not None:
        if float(day.get("total_precip_mm", 0.0)) <= float(min_precip):
            return False
        return True
    threshold = rule.get("humidity_threshold")
    if threshold is None:
        return True
    hours = _humidity_hours(day, int(threshold))
    return hours >= int(rule["min_humidity_hours"])


def count_favorable_days(
    daily_records: list[Mapping[str, Any]], rule: Mapping[str, Any]
) -> int:
    """Count favorable days in the provided (12-day) window."""
    return sum(1 for day in daily_records if is_favorable_day(day, rule))


def risk_level(favorable_days: int, confidence: float) -> str:
    """Map favorable-day count and model confidence to a risk label."""
    if favorable_days >= 5 or (favorable_days >= 3 and confidence >= 0.7):
        return "high"
    if favorable_days >= 2:
        return "moderate"
    return "low"


def unknown_risk(reason: str) -> dict[str, Any]:
    """Build a risk payload when weather or rules cannot be applied."""
    return {
        "level": "unknown",
        "favorable_days": 0,
        "window_days": WINDOW_DAYS,
        "reason": reason,
    }


def assess(
    candidate: Mapping[str, Any], daily_records: list[Mapping[str, Any]] | None
) -> dict[str, Any]:
    """Return the API risk object for one candidate and daily weather."""
    if daily_records is None:
        return unknown_risk(
            "Weather data could not be fetched, so disease risk is unknown."
        )
    disease = str(candidate.get("disease", ""))
    confidence = float(candidate.get("confidence", 0.0))
    rule = RULES.get(disease)
    if rule is None:
        return {
            "level": "low",
            "favorable_days": 0,
            "window_days": WINDOW_DAYS,
            "reason": f"No weather-risk rule is defined for {disease}.",
        }
    favorable = count_favorable_days(daily_records, rule)
    level = risk_level(favorable, confidence)
    reason = (
        f"{disease} is favored when {rule['summary']}. "
        f"That pattern occurred on {favorable} of {WINDOW_DAYS} days. "
        f"With model confidence {confidence:.2f}, risk is {level}."
    )
    return {
        "level": level,
        "favorable_days": favorable,
        "window_days": WINDOW_DAYS,
        "reason": reason,
    }
