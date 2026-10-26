"""API tests with mocked diagnosis and weather services."""

from __future__ import annotations

import os
import tempfile
from io import BytesIO
from pathlib import Path

os.environ["GEMINI_API_KEY"] = "test-key-not-real"
_DB = tempfile.NamedTemporaryFile(prefix="cropwatch-test-", suffix=".db", delete=False)
_DB.close()
os.environ["DATABASE_PATH"] = _DB.name

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402
from app.storage import init_db, save_diagnosis  # noqa: E402

init_db()
client = TestClient(app)


def _jpeg_file(name: str = "leaf.jpg") -> tuple[str, bytes, str]:
    image = Image.new("RGB", (64, 48), color=(30, 140, 40))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return (name, buffer.getvalue(), "image/jpeg")


def _fake_weather(_lat: float, _lon: float) -> tuple[list[dict], dict]:
    daily = [
        {
            "date": "2026-10-20",
            "mean_temp_c": 26.0,
            "humidity_hours_above_85": 12,
            "humidity_hours_above_90": 8,
            "total_precip_mm": 1.5,
        }
        for _ in range(12)
    ]
    summary = {"avg_temp_c": 24.1, "avg_humidity_pct": 88.0, "total_rain_mm": 31.2}
    return daily, summary


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diagnose_success(monkeypatch) -> None:
    def fake_diagnose(*_args, **_kwargs):
        return [
            {
                "disease": "Early blight",
                "confidence": 0.82,
                "description": "Concentric leaf spots on older foliage.",
            },
            {
                "disease": "Septoria leaf spot",
                "confidence": 0.10,
                "description": "Small specks with pale centers.",
            },
            {
                "disease": "Healthy",
                "confidence": 0.05,
                "description": "Most tissue looks green.",
            },
        ]

    monkeypatch.setattr("app.main.diagnose_image", fake_diagnose)
    monkeypatch.setattr("app.main.fetch_weather", _fake_weather)
    filename, data, content_type = _jpeg_file()
    response = client.post(
        "/diagnose",
        files={"image": (filename, data, content_type)},
        data={
            "crop": "tomato",
            "latitude": "12.97",
            "longitude": "77.59",
            "symptoms": "spots,yellowing",
            "plants_affected_percent": "20",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["crop"] == "tomato"
    assert body["candidates"][0]["disease"] == "Early blight"
    assert body["candidates"][0]["confidence"] == 0.82
    assert body["risk"]["level"] in {"low", "moderate", "high"}
    assert body["advice"]["low_confidence"] is False
    assert "avg_temp_c" in body["weather_summary"]
    assert body["id"]
    assert body["created_at"]


def test_diagnose_rejects_bad_file_type() -> None:
    response = client.post(
        "/diagnose",
        files={"image": ("notes.txt", b"hello", "text/plain")},
        data={"crop": "tomato", "latitude": "0", "longitude": "0"},
    )
    assert response.status_code == 400
    assert "JPEG or PNG" in response.json()["detail"]


def test_diagnose_invalid_crop_returns_422() -> None:
    filename, data, content_type = _jpeg_file()
    response = client.post(
        "/diagnose",
        files={"image": (filename, data, content_type)},
        data={"crop": "banana", "latitude": "0", "longitude": "0"},
    )
    assert response.status_code == 422


def test_diagnose_low_confidence_path(monkeypatch) -> None:
    def fake_diagnose(*_args, **_kwargs):
        return [
            {
                "disease": "Early blight",
                "confidence": 0.41,
                "description": "Unclear spots.",
            }
        ]

    monkeypatch.setattr("app.main.diagnose_image", fake_diagnose)
    monkeypatch.setattr("app.main.fetch_weather", _fake_weather)
    filename, data, content_type = _jpeg_file()
    response = client.post(
        "/diagnose",
        files={"image": (filename, data, content_type)},
        data={"crop": "potato", "latitude": "1.2", "longitude": "36.8"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["advice"]["low_confidence"] is True
    assert "extension" in body["advice"]["expert_referral"].lower()


def test_history_and_treatment_log() -> None:
    init_db()
    save_diagnosis(
        {
            "id": "diag-1",
            "created_at": "2026-10-26T00:00:00+00:00",
            "crop": "rice",
            "candidates": [],
            "risk": {
                "level": "low",
                "favorable_days": 0,
                "window_days": 12,
                "reason": "n/a",
            },
            "advice": {
                "message": "n/a",
                "steps": ["step"],
                "low_confidence": True,
                "expert_referral": "Contact your local agricultural extension office.",
            },
            "weather_summary": {
                "avg_temp_c": 0.0,
                "avg_humidity_pct": 0.0,
                "total_rain_mm": 0.0,
            },
        }
    )
    history = client.get("/history?limit=5")
    assert history.status_code == 200
    assert any(item["id"] == "diag-1" for item in history.json()["items"])
    logged = client.post(
        "/treatment-log",
        json={
            "diagnosis_id": "diag-1",
            "treatment": "Removed infected leaves",
            "date": "2026-10-26",
        },
    )
    assert logged.status_code == 200
    assert logged.json()["diagnosis_id"] == "diag-1"


def teardown_module(_module) -> None:
    path = Path(_DB.name)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
