# Live Earthquake Dashboard (Flask + JavaScript)

Deployable Flask app for **live earthquake visualization** on Render, with resilient caching and two UI views:
- Chart dashboard (`/dashboard`)
- Interactive 3D globe (`/globe`) powered by `globe.gl`

## Features

- Uses the **USGS live GeoJSON feed** (`all_day`) as primary data source.
- Caches latest feed data in SQLite (`data/earthquakes.db`) for reliability when the external API is temporarily unavailable.
- Exposes `GET /api/earthquakes` with magnitude/geo filters and optional force refresh.
- Includes:
  - chart-based dashboard for quick analytics
  - 3D globe visualization with tooltip details, magnitude sizing/coloring, and auto-refresh controls
- Ready for Render deployment with Gunicorn via `Procfile`.

## Architecture

- **Backend:** Flask (`main.py`)
- **Data Source:** USGS Earthquake Feed
- **Cache:** SQLite local cache (auto-created)
- **Frontend:**
  - `templates/dashboard.html` (Chart.js dashboard)
  - `templates/globe.html` + `static/js/globe.js` + `static/css/globe.css` (`globe.gl` view)

## Routes

- `/` and `/dashboard`: existing dashboard view
- `/globe`: new 3D globe visualization page
- `/api/earthquakes`: JSON data endpoint used by both views
- `/health`: health check endpoint

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

Open:
- Dashboard: `http://localhost:5000/dashboard`
- 3D globe: `http://localhost:5000/globe`

## Globe view behavior

The globe view calls `/api/earthquakes` directly and maps data as follows:
- `lat` ← `latitude`
- `lng` ← `longitude`
- point radius/altitude scale with `magnitude`
- point color reflects magnitude severity bands
- tooltip includes place, magnitude, depth, and time

UI controls include:
- minimum magnitude filter
- recent time window filter (last 24h/12h/6h/3h or all cached points)
- color mode toggle (magnitude or depth)
- maximum rendered points cap
- point height scaling slider
- auto-refresh toggle (2-minute interval)
- auto-rotate toggle
- manual refresh button
- magnitude color legend
- status, count, source, and last updated timestamp

Interaction:
- hover a point for details
- click a point to focus the camera on that earthquake

If data is empty or unavailable, the page shows friendly status messaging instead of crashing.

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
- If USGS is unreachable, the app serves last cached records.
- This behavior is suitable for Render free/limited instances with occasional transient network failures.
