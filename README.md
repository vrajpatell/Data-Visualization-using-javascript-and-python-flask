# Live Earthquake Dashboard (Flask + JavaScript)

Deployable Flask dashboard for **live earthquake data** on Render, with resilient caching.

## What changed

- Uses the **USGS live GeoJSON feed** (`all_day`) as primary data source.
- Caches latest feed data in SQLite (`data/earthquakes.db`) for reliability when external API is temporarily unavailable.
- Exposes a single API endpoint with filters: `GET /api/earthquakes`.
- Includes force refresh support (`refresh=1`) from the dashboard.
- Ready for Render with Gunicorn via `Procfile`.

## Architecture

- **Backend:** Flask (`main.py`)
- **Data Source:** USGS Earthquake Feed
- **Cache:** SQLite local cache (auto-created)
- **Frontend:** Chart.js dashboard (`templates/dashboard.html`)

## API

### `GET /api/earthquakes`

Query params:
- `mag_min`, `mag_max`
- `lat1`, `lat2`
- `lon1`, `lon2`
- `refresh=1` (optional force live refresh)

Response shape:

```json
{
  "meta": {
    "source": "live|cache|fallback_cache|bootstrap_cache",
    "refresh_result": "live|cache|fallback_cache|bootstrap_cache",
    "last_refresh_epoch": 0,
    "count": 0,
    "filters": {}
  },
  "data": [
    {
      "id": "...",
      "time_ms": 0,
      "place": "...",
      "magnitude": 0,
      "latitude": 0,
      "longitude": 0,
      "depth": 0
    }
  ]
}
```

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Open: `http://localhost:5000`


## Deploy to Render

This repository includes both:
- `Procfile` (classic process command)
- `render.yaml` (Render Blueprint / IaC)

### Option A: Deploy via `render.yaml` (recommended)

1. Push the repo to GitHub.
2. In Render, choose **New +** → **Blueprint**.
3. Select this repository and apply the blueprint.

### Option B: Manual Web Service setup

1. Push the repo to GitHub.
2. In Render, create a **Web Service** from the repo.
3. Runtime: Python 3.
4. Build command:
   ```bash
   pip install -r requirements.txt
   ```
5. Start command:
   ```bash
   gunicorn main:app --bind 0.0.0.0:$PORT
   ```
6. Optional environment variables:
   - `CACHE_TTL_SECONDS=300`
   - `USGS_FEED_URL=https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`

## Health check

`GET /health` returns:

```json
{"status":"ok"}
```

## Notes

- On startup, the app creates cache tables and attempts refresh.
- If USGS is unreachable, app serves last cached records.
- This behavior is ideal for Render free/limited instances where transient network failures can occur.
