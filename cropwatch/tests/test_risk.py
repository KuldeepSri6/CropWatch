"""Unit tests for the weather-risk engine."""

from __future__ import annotations

from app.risk import RULES, assess, is_favorable_day, risk_level


def _day(
    mean_temp_c: float,
    humidity_hours_above_85: int = 0,
    humidity_hours_above_90: int = 0,
    total_precip_mm: float = 0.0,
) -> dict[str, float | int]:
    return {
        "mean_temp_c": mean_temp_c,
        "humidity_hours_above_85": humidity_hours_above_85,
        "humidity_hours_above_90": humidity_hours_above_90,
        "total_precip_mm": total_precip_mm,
    }


def test_early_blight_favorable_at_exactly_24c() -> None:
    """24 C is inside the Early blight temperature band."""
    day = _day(24.0, humidity_hours_above_90=6)
    assert is_favorable_day(day, RULES["Early blight"]) is True


def test_early_blight_not_favorable_just_below_24c() -> None:
    day = _day(23.99, humidity_hours_above_90=6)
    assert is_favorable_day(day, RULES["Early blight"]) is False


def test_leaf_mold_humidity_exactly_85_is_not_above() -> None:
    """Hours at exactly 85% must not count as humidity above 85%."""
    day = _day(22.0, humidity_hours_above_85=0, humidity_hours_above_90=0)
    assert is_favorable_day(day, RULES["Leaf mold"]) is False


def test_leaf_mold_counts_hours_strictly_above_85() -> None:
    day = _day(22.0, humidity_hours_above_85=8)
    assert is_favorable_day(day, RULES["Leaf mold"]) is True


def test_risk_level_high_from_five_favorable_days() -> None:
    assert risk_level(5, 0.4) == "high"


def test_risk_level_high_from_three_days_and_high_confidence() -> None:
    assert risk_level(3, 0.7) == "high"


def test_risk_level_moderate_from_two_days() -> None:
    assert risk_level(2, 0.9) == "moderate"


def test_risk_level_low_from_one_day() -> None:
    assert risk_level(1, 0.9) == "low"


def test_assess_with_fake_daily_records() -> None:
    daily = [_day(26.0, humidity_hours_above_90=8) for _ in range(12)]
    result = assess(
        {"disease": "Early blight", "confidence": 0.82, "description": "spots"},
        daily,
    )
    assert result["level"] == "high"
    assert result["favorable_days"] == 12
    assert result["window_days"] == 12
    assert "Early blight" in result["reason"]


def test_assess_unknown_when_weather_missing() -> None:
    result = assess({"disease": "Early blight", "confidence": 0.9}, None)
    assert result["level"] == "unknown"
    assert result["favorable_days"] == 0
