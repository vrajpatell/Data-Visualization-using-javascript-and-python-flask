import json
import os
import random
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any
from urllib.error import URLError
from urllib.request import urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", DATA_DIR / "earthquakes.db"))
USGS_FEED_URL = os.getenv(
    "USGS_FEED_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS earthquakes (
                id TEXT PRIMARY KEY,
                time_ms INTEGER,
                place TEXT,
                magnitude REAL,
                latitude REAL,
                longitude REAL,
                depth REAL,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO metadata(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _get_metadata(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def parse_geojson_features(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    features = payload.get("features", [])
    parsed = []
    for f in features:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [None, None, None])
        quake_id = f.get("id")
        if quake_id is None or coords[0] is None or coords[1] is None:
            continue
        magnitude = props.get("mag")
        if magnitude is None:
            continue
        parsed.append(
            {
                "id": str(quake_id),
                "time_ms": int(props.get("time") or 0),
                "place": str(props.get("place") or "Unknown"),
                "magnitude": float(magnitude),
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "depth": float(coords[2] or 0.0),
            }
        )
    return parsed


def fetch_live_usgs() -> List[Dict[str, Any]]:
    with urlopen(USGS_FEED_URL, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return parse_geojson_features(payload)


def replace_cache(rows: List[Dict[str, Any]]) -> None:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM earthquakes")
        conn.executemany(
            """
            INSERT INTO earthquakes(id, time_ms, place, magnitude, latitude, longitude, depth, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            [
                (
                    r["id"],
                    r["time_ms"],
                    r["place"],
                    r["magnitude"],
                    r["latitude"],
                    r["longitude"],
                    r["depth"],
                    now,
                )
                for r in rows
            ],
        )
        _set_metadata(conn, "last_refresh_epoch", str(now))
        _set_metadata(conn, "last_refresh_source", "live")
        conn.commit()


def refresh_cache_if_needed(force: bool = False) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        last_refresh = int(_get_metadata(conn, "last_refresh_epoch", "0") or "0")

    is_stale = int(time.time()) - last_refresh > CACHE_TTL_SECONDS
    if not force and not is_stale:
        return "cache"

    try:
        rows = fetch_live_usgs()
        if rows:
            replace_cache(rows)
            return "live"
    except (URLError, TimeoutError, ValueError, OSError):
        pass

    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM earthquakes").fetchone()[0]
        if count == 0:
            # Ensure UI still renders if first live fetch fails in restricted environments.
            conn.commit()
            seed_bootstrap_data_if_empty()
            return "bootstrap_cache"
        _set_metadata(conn, "last_refresh_source", "fallback_cache")
        conn.commit()
    return "fallback_cache"


def query_quakes(
    mag_min: float,
    mag_max: float,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, time_ms, place, magnitude, latitude, longitude, depth
            FROM earthquakes
            WHERE magnitude BETWEEN ? AND ?
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            ORDER BY time_ms DESC
            """,
            (mag_min, mag_max, lat_min, lat_max, lon_min, lon_max),
        ).fetchall()
        source = _get_metadata(conn, "last_refresh_source", "cache")
        refreshed = int(_get_metadata(conn, "last_refresh_epoch", "0") or "0")

    payload = [
        {
            "id": r[0],
            "time_ms": r[1],
            "place": r[2],
            "magnitude": r[3],
            "latitude": r[4],
            "longitude": r[5],
            "depth": r[6],
        }
        for r in rows
    ]
    return payload, source, refreshed

def seed_bootstrap_data_if_empty() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM earthquakes").fetchone()[0]
        if existing > 0:
            return

        rng = random.Random(7)
        now = int(time.time())
        rows = []
        for i in range(220):
            rows.append(
                (
                    f"bootstrap-{i}",
                    (now - i * 1800) * 1000,
                    "Bootstrap cached sample",
                    round(rng.uniform(1.0, 6.8), 1),
                    round(rng.uniform(-70, 70), 3),
                    round(rng.uniform(-170, 170), 3),
                    round(rng.uniform(1, 120), 1),
                    now,
                )
            )

        conn.executemany(
            """
            INSERT INTO earthquakes(id, time_ms, place, magnitude, latitude, longitude, depth, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        _set_metadata(conn, "last_refresh_epoch", str(now))
        _set_metadata(conn, "last_refresh_source", "bootstrap_cache")
        conn.commit()


def parse_float(name: str, default: float) -> float:
    raw = request.values.get(name, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/earthquakes")
def api_earthquakes():
    mag_min = parse_float("mag_min", 0.0)
    mag_max = parse_float("mag_max", 10.0)
    lat1 = parse_float("lat1", -90.0)
    lat2 = parse_float("lat2", 90.0)
    lon1 = parse_float("lon1", -180.0)
    lon2 = parse_float("lon2", 180.0)
    force_refresh = request.args.get("refresh", "0") == "1"

    mag_min, mag_max = sorted((mag_min, mag_max))
    lat_min, lat_max = sorted((lat1, lat2))
    lon_min, lon_max = sorted((lon1, lon2))

    refresh_result = refresh_cache_if_needed(force=force_refresh)
    rows, source, refreshed = query_quakes(mag_min, mag_max, lat_min, lat_max, lon_min, lon_max)

    return jsonify(
        {
            "meta": {
                "source": source,
                "refresh_result": refresh_result,
                "last_refresh_epoch": refreshed,
                "count": len(rows),
                "filters": {
                    "mag_min": mag_min,
                    "mag_max": mag_max,
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max,
                },
            },
            "data": rows,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


init_db()
refresh_cache_if_needed(force=False)
seed_bootstrap_data_if_empty()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
