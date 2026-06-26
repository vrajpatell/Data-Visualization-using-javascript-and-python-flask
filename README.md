# QuakeRisk: Earthquake Monitoring & Probabilistic Forecasting Dashboard

A production-ready Flask application for monitoring USGS GeoJSON earthquake feeds, caching records in SQLite, visualizing activity with Chart.js/Leaflet/globe.gl, and providing **experimental probabilistic earthquake forecasting**.

> Scientific disclaimer: earthquakes cannot be predicted deterministically with reliable exact time, location, and magnitude. This app only provides regional risk scoring, magnitude likelihood estimation, aftershock/seismic activity trend analysis, and educational uncertainty warnings.

## Screenshots

Add screenshots after deployment for the dashboard, 2D map, 3D globe, and forecast page.

## Architecture

- `main.py` keeps `gunicorn main:app` compatibility.
- `app/__init__.py` creates the Flask app.
- `app/routes.py` exposes HTML pages and JSON APIs.
- `app/services/usgs_client.py` fetches/parses USGS GeoJSON.
- `app/services/cache.py` manages SQLite tables, indexes, upserts, and refresh metadata.
- `app/services/analytics.py` powers dashboard summary aggregations.
- `app/services/model.py` implements a heuristic baseline plus optional scikit-learn classifier.
- `templates/` and `static/` contain responsive frontend pages.
- `tests/` contains pytest coverage for parsing, cache, APIs, and forecast fallback.

## Routes

HTML: `/dashboard`, `/map`, `/globe`, `/forecast`, `/about`.

APIs: `/api/earthquakes`, `/api/summary`, `/api/regions`, `/api/timeseries`, `/api/forecast`, `/api/model/status`, `POST /api/model/train`, `/health`, `/api/health/deep`.

## API examples

```bash
curl 'http://localhost:5000/api/earthquakes?feed=day&mag_min=2.5&limit=100'
curl 'http://localhost:5000/api/summary?feed=7day'
curl 'http://localhost:5000/api/forecast?lat=37.7749&lon=-122.4194&radius_km=300&hours=72&min_magnitude=2.5'
```

## ML forecast explanation

The forecast endpoint returns a 0-100 risk score, bucket, expected activity count, model confidence, top contributing features, nearby events, and a warning. It always works through a baseline heuristic; if enough cached data exists, `POST /api/model/train` can train a scikit-learn classifier saved with joblib.

Training is time-aware and reports accuracy, precision, recall, F1, confusion matrix, and ROC AUC when valid. It avoids deterministic claims and should not be used for emergency decisions.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open <http://localhost:5000/dashboard>.

## Render deployment

The included `Procfile` and `render.yaml` use:

```bash
gunicorn main:app --bind 0.0.0.0:$PORT
```

Health check path: `/health`.

SQLite works out of the box for Render free-tier compatibility, but local disk can be ephemeral. For durable history, attach a Render persistent disk and set `SQLITE_DB_PATH` to that mount, or migrate the cache layer to Postgres later.

## Environment variables

See `.env.example` for all supported settings: `USGS_FEED_URL`, `CACHE_TTL_SECONDS`, `SQLITE_DB_PATH`, `DEFAULT_FEED_WINDOW`, `MODEL_PATH`, `ENABLE_BOOTSTRAP_DATA`, `ENABLE_MODEL_TRAINING_ON_STARTUP`, `MAX_API_LIMIT`, and `ADMIN_TOKEN`.

## Model training

Set `ADMIN_TOKEN`, then call:

```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" http://localhost:5000/api/model/train
```

If no token is configured, the training endpoint is disabled.

## Tests

```bash
pytest
python -m compileall .
```

## Troubleshooting

- If USGS is unavailable, APIs fall back to cached or clearly labeled bootstrap/demo data.
- If CDN assets fail, the 2D map and dashboard still provide monitoring views.
- If model training reports insufficient data, continue using the heuristic forecast until more cache history exists.

## Future improvements

- Persistent Postgres backend.
- Region-specific model calibration.
- Background scheduled ingestion.
- Authentication for admin operations.
- Screenshot automation for README assets.

## Multi-source earthquake data and coordinate safety

This Flask dashboard ingests public earthquake observations, normalizes every event into canonical `latitude` and `longitude` fields, stores them in SQLite, and serves the map, globe, dashboard, and probabilistic forecast from the same filtered API path.

### Wrong-location bug fix

The map/globe coordinate order was not globally swapped. USGS GeoJSON correctly uses `[longitude, latitude, depth]`, Leaflet correctly uses `[latitude, longitude]`, and globe.gl correctly uses `{ lat, lng }`. Wrong-looking points were primarily caused by random bootstrap demo records being mixed with real cached feeds, feed-specific cache results not being strictly filtered, bootstrap cache being treated as fresh data, and longitude bounds being sorted across the antimeridian. The API now excludes bootstrap records by default, filters by `source` and `source_feed`, tracks refresh metadata per source/feed, validates coordinates before storage, and handles dateline-crossing viewports with `longitude >= west OR longitude <= east`.

### Coordinate normalization rules

Different sources use different coordinate order. This app normalizes every source into canonical latitude/longitude fields before storage and visualization.

* Backend canonical fields are always `latitude` and `longitude`.
* Leaflet receives `[latitude, longitude]`.
* globe.gl receives `{ lat: latitude, lng: longitude }`.
* USGS GeoJSON, USGS FDSN GeoJSON, and GeoNet GeoJSON parse `[longitude, latitude, depth]`.
* BMKG `Coordinates` parse as `latitude,longitude`.
* Invalid, NaN, infinite, out-of-range, or silently swapped-invalid coordinates are rejected before reaching the frontend.

### Public data sources

| Source | Coverage | Format | Role |
| --- | --- | --- | --- |
| USGS GeoJSON | Global | GeoJSON | Primary live source |
| USGS FDSN | Global | GeoJSON/CSV/XML | Historical and custom search |
| EMSC / SeismicPortal | Europe/global | FDSN JSON/QuakeML/CSV | Cross-checking |
| ISC | Global reviewed catalogue | FDSN | Historical/reviewed (stubbed if unavailable) |
| GFZ/GEOFON | Global/Europe | FDSN | Additional global source (stubbed if unavailable) |
| BMKG | Indonesia | JSON/XML | Asia/Indonesia |
| GeoNet | New Zealand | GeoJSON/JSON | Oceania/New Zealand |
| AusPass | Australia/Oceania | FDSN | Optional, disabled by default |

### Attribution

Data remains attributed in `/api/sources` and frontend status areas. Primary attribution includes USGS Earthquake Hazards Program, EMSC / SeismicPortal, BMKG Indonesia, GeoNet, ISC, GFZ/GEOFON, and AusPass where enabled.

### Environment variables

Recommended production settings:

```text
ENABLE_BOOTSTRAP_DATA=false
ALLOW_BOOTSTRAP_AS_FRESH_CACHE=false
ENABLED_SOURCES=usgs_geojson,usgs_fdsn,emsc,isc,geofon,bmkg,geonet
SOURCE_TIMEOUT_SECONDS=15
SOURCE_MAX_RETRIES=2
SOURCE_REFRESH_TTL_SECONDS=300
MAX_API_LIMIT=2000
ADMIN_TOKEN=change-me
SECRET_KEY=change-me
```

### API examples

```bash
curl '/api/earthquakes?source=usgs&feed=day&include_demo=false'
curl '/api/earthquakes?source=usgs&feed=30day&mag_min=4.5'
curl '/api/earthquakes?source=all&feed=day&lon1=170&lon2=-170'
curl '/api/sources'
curl -X POST '/api/refresh' -H 'Content-Type: application/json' -d '{"source":"all","feed":"day"}'
```

If demo records are explicitly requested with `include_demo=true`, the API and UI warn: “Demo data — not real earthquake locations.”

### Render deployment

Keep deployment simple:

```bash
pip install -r requirements.txt
gunicorn main:app --bind 0.0.0.0:$PORT
```

Set `ENABLE_BOOTSTRAP_DATA=false` on Render so random bootstrap records are never displayed as real earthquake locations.

### Local verification

Run:

```bash
pytest
python -m compileall .
```

Open `/map` and `/globe`, select a source/feed, and test a dateline viewport near Alaska, Japan, Fiji, New Zealand, Indonesia, or the Pacific.

### Scientific disclaimer

The forecast page is probabilistic and educational. It summarizes recent regional seismicity and model-derived risk indicators; it does not predict exact earthquakes, times, or locations.
