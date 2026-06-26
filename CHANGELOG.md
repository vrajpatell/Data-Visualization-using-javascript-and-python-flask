# Changelog

## 2026-06-26

- Refactored the Flask app into an application factory and service modules.
- Added robust SQLite cache schema, indexes, upserts, refresh metadata, and fallback handling.
- Added summary, regions, timeseries, forecast, model status/train, and deep health APIs.
- Added probabilistic risk scoring with heuristic fallback and optional scikit-learn training.
- Rebuilt dashboard, added Leaflet map, forecast page, and about page.
- Updated Render deployment, dependencies, environment documentation, tests, and CI.
