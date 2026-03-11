# Data Visualization Dashboard (Flask + JavaScript)

A deployable Flask dashboard for exploring earthquake-like geospatial data with interactive charts.

## What this project now includes

- A **single-page dashboard** at `/` and `/dashboard`.
- Interactive filters by:
  - **Magnitude range**
  - **Latitude/Longitude bounding box**
- Four client-side chart types (Chart.js):
  - Line chart (magnitude trend)
  - Bar chart (latitude sample)
  - Pie chart (magnitude buckets)
  - Scatter chart (longitude vs latitude)
- KPI summary cards:
  - Total points
  - Average magnitude
  - Max magnitude
- A `/health` endpoint for platform health checks.
- A SQLite fallback dataset (auto-seeded) so the app runs out-of-the-box in local/dev/deploy environments.

---

## Architecture

- **Backend:** Flask (`main.py`)
- **Frontend:** HTML + vanilla JavaScript + Chart.js CDN (`templates/dashboard.html`)
- **Data store:** SQLite database file at `data/earthquakes.db` by default

### API Endpoints

- `GET /api/magnitude?mag_min=2&mag_max=6`
  - Returns points filtered by magnitude range.
- `GET /api/bounds?lat1=-30&lat2=30&lon1=-60&lon2=60`
  - Returns points filtered by lat/lon box.
- `GET /health`
  - Returns service health JSON.

---

## Local Development

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the app

```bash
python main.py
```

App starts at: `http://localhost:5000`

---

## Deployment (Render-ready)

This repository includes a `Procfile` for deployment process declaration.

### Recommended process command

Use Gunicorn in production:

```bash
gunicorn main:app --bind 0.0.0.0:$PORT
```

If your platform reads `Procfile`, this is already configured.

### Environment variables

- `PORT` (set by hosting provider)
- `SQLITE_DB_PATH` (optional; defaults to `data/earthquakes.db`)

---

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── Procfile
├── data/
│   └── earthquakes.db         # auto-generated at runtime
└── templates/
    └── dashboard.html
```

---

## Notes

- The app auto-creates and seeds SQLite data if no rows exist.
- This makes first deploy deterministic and avoids hard-coded external DB credentials.
- Existing legacy visualization templates remain in the repo but are not used by default routes.

---

## Quick Verification

```bash
curl http://localhost:5000/health
curl "http://localhost:5000/api/magnitude?mag_min=3&mag_max=5"
curl "http://localhost:5000/api/bounds?lat1=-10&lat2=10&lon1=-20&lon2=20"
```

