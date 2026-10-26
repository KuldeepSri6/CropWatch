# CropWatch backend

FastAPI service for a hackathon web app that helps smallholder farmers detect crop diseases from a leaf photo and estimate weather-driven disease risk for the next few days.

Supported crops: `tomato`, `potato`, `maize`, `rice`.

## Setup

Python 3.11+ is required (3.13 is fine).

```powershell
cd cropwatch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux:

```bash
cd cropwatch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY`. Never commit that file.

## Run

From the project root:

```powershell
uvicorn app.main:app --reload
```

The API listens on http://127.0.0.1:8000. CORS allows `http://localhost:5173` plus any extra origins in `ALLOWED_ORIGINS`.

## Example: diagnose a leaf

```powershell
curl -X POST "http://127.0.0.1:8000/diagnose" `
  -F "image=@leaf.jpg;type=image/jpeg" `
  -F "crop=tomato" `
  -F "latitude=12.97" `
  -F "longitude=77.59" `
  -F "symptoms=spots,yellowing" `
  -F "plants_affected_percent=20"
```

Other endpoints:

- `GET /health` — `{"status":"ok"}`
- `GET /history?limit=20` — recent diagnoses
- `POST /treatment-log` — JSON `{"diagnosis_id":"...","treatment":"...","date":"YYYY-MM-DD"}`

## Tests

```powershell
pytest
```

`test_api.py` mocks Gemini and Open-Meteo so tests do not need a live API key. `GEMINI_API_KEY` is still required at process start for the real server.

## Assumptions

- The project folder is `cropwatch` (workspace name). The inner layout matches the spec (`app/`, `tests/`, and the listed files).
- Daily weather records store both hours with humidity **above 85%** and **above 90%**, so Early blight / Late blight rules can use the 90% threshold.
- Temperature rule bounds are inclusive; humidity and precipitation thresholds are strict (“above”).
- The response `risk` object is computed from the **top** candidate. If weather fetch fails, diagnosis still succeeds with `risk.level` = `unknown` and zeroed `weather_summary` values.
- `python-multipart` is pinned because FastAPI needs it for `multipart/form-data`.
- Treatment advice names no specific chemicals; it always points farmers to a local extension officer.
- `plants_affected_percent` is accepted and forwarded to Gemini as context; it is not a separate field in the JSON response.
- Gemini timeouts are set to 30 seconds via `HttpOptions(timeout=30000)` (milliseconds). JSON parse failures retry the model call once, then the API returns HTTP 502 without stack traces or keys.
