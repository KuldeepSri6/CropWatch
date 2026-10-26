"""Open-Meteo weather fetch, daily aggregation, and short-term cache."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10.0
CACHE_TTL_SECONDS = 30 * 60
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation"

_cache: dict[tuple[float, float], tuple[float, tuple[list[dict[str, Any]], dict[str, float]]]] = {}
_cache_lock = threading.Lock()


class WeatherError(Exception):
    """Raised when Open-Meteo cannot be fetched or parsed."""


def _cache_key(latitude: float, longitude: float) -> tuple[float, float]:
    return (round(latitude, 2), round(longitude, 2))


def _from_cache(
    key: tuple[float, float],
) -> tuple[list[dict[str, Any]], dict[str, float]] | None:
    with _cache_lock:
        hit = _cache.get(key)
        if hit is None:
            return None
        stored_at, payload = hit
        if time.monotonic() - stored_at > CACHE_TTL_SECONDS:
            _cache.pop(key, None)
            return None
        return payload


def _store_cache(
    key: tuple[float, float],
    payload: tuple[list[dict[str, Any]], dict[str, float]],
) -> None:
    with _cache_lock:
        _cache[key] = (time.monotonic(), payload)


def _daily_from_hourly(hourly: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Aggregate Open-Meteo hourly series into per-day records."""
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    hums = hourly.get("relative_humidity_2m") or []
    precs = hourly.get("precipitation") or []
    if not (len(times) == len(temps) == len(hums) == len(precs)):
        raise WeatherError("Weather hourly arrays are incomplete.")
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"temps": [], "hums": [], "prec": 0.0, "h85": 0, "h90": 0}
    )
    for stamp, temp, humidity, precip in zip(times, temps, hums, precs):
        if temp is None or humidity is None or precip is None:
            continue
        day = str(stamp)[:10]
        bucket = buckets[day]
        bucket["temps"].append(float(temp))
        bucket["hums"].append(float(humidity))
        bucket["prec"] += float(precip)
        if float(humidity) > 85:
            bucket["h85"] += 1
        if float(humidity) > 90:
            bucket["h90"] += 1
    records = []
    for day in sorted(buckets):
        bucket = buckets[day]
        if not bucket["temps"]:
            continue
        records.append(
            {
                "date": day,
                "mean_temp_c": sum(bucket["temps"]) / len(bucket["temps"]),
                "humidity_hours_above_85": bucket["h85"],
                "humidity_hours_above_90": bucket["h90"],
                "total_precip_mm": bucket["prec"],
            }
        )
    if not records:
        raise WeatherError("No usable daily weather records were returned.")
    return records


def _summary(
    daily_records: list[dict[str, Any]], hourly: dict[str, list[Any]]
) -> dict[str, float]:
    """Build the compact weather_summary object for the API response."""
    temps = [float(v) for v in (hourly.get("temperature_2m") or []) if v is not None]
    hums = [
        float(v) for v in (hourly.get("relative_humidity_2m") or []) if v is not None
    ]
    rain = sum(float(day["total_precip_mm"]) for day in daily_records)
    avg_temp = sum(temps) / len(temps) if temps else 0.0
    avg_hum = sum(hums) / len(hums) if hums else 0.0
    return {
        "avg_temp_c": round(avg_temp, 1),
        "avg_humidity_pct": round(avg_hum, 1),
        "total_rain_mm": round(rain, 1),
    }


def _request_forecast(latitude: float, longitude: float) -> dict[str, Any]:
    """Call the Open-Meteo forecast endpoint."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARS,
        "past_days": 7,
        "forecast_days": 5,
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.get(FORECAST_URL, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        logger.error("Open-Meteo request timed out: %s", exc)
        raise WeatherError("Weather request timed out.") from exc
    except httpx.HTTPError as exc:
        logger.error("Open-Meteo request failed: %s", exc)
        raise WeatherError("Weather request failed.") from exc
    except ValueError as exc:
        logger.error("Open-Meteo returned invalid JSON: %s", exc)
        raise WeatherError("Weather response was invalid.") from exc


def fetch_weather(
    latitude: float, longitude: float
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Return daily records and a summary for the 12-day window.

    Results are cached in memory for 30 minutes, keyed by coordinates
    rounded to two decimal places.
    """
    key = _cache_key(latitude, longitude)
    cached = _from_cache(key)
    if cached is not None:
        return cached
    payload = _request_forecast(latitude, longitude)
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherError("Weather response was missing hourly data.")
    daily = _daily_from_hourly(hourly)
    summary = _summary(daily, hourly)
    result = (daily, summary)
    _store_cache(key, result)
    return result
