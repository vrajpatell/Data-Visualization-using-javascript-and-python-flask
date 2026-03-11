import os
import random
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", DATA_DIR / "earthquakes.db"))


def init_sqlite_db() -> None:
    """Create a local SQLite database with sample data if missing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS all_month (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                mag REAL NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM all_month").fetchone()[0]
        if count == 0:
            rng = random.Random(42)
            rows = [
                (
                    round(rng.uniform(-75.0, 75.0), 2),
                    round(rng.uniform(-180.0, 180.0), 2),
                    round(rng.uniform(1.0, 8.0), 1),
                )
                for _ in range(600)
            ]
            conn.executemany(
                "INSERT INTO all_month(latitude, longitude, mag) VALUES(?,?,?)", rows
            )
            conn.commit()


def get_sqlite_rows_by_magnitude(mag_min: float, mag_max: float):
    with sqlite3.connect(DB_PATH) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT latitude, longitude, mag
                FROM all_month
                WHERE mag BETWEEN ? AND ?
                ORDER BY latitude
                """,
                (mag_min, mag_max),
            )
            return cur.fetchall()


def get_sqlite_rows_by_bounds(lat_min: float, lat_max: float, lon_min: float, lon_max: float):
    with sqlite3.connect(DB_PATH) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT latitude, longitude, mag
                FROM all_month
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
                ORDER BY latitude
                """,
                (lat_min, lat_max, lon_min, lon_max),
            )
            return cur.fetchall()


def parse_float(name: str, default: float) -> float:
    raw = request.values.get(name, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/magnitude")
def api_magnitude():
    mag_min = parse_float("mag_min", 2.0)
    mag_max = parse_float("mag_max", 6.0)
    if mag_min > mag_max:
        mag_min, mag_max = mag_max, mag_min

    rows = get_sqlite_rows_by_magnitude(mag_min, mag_max)
    payload = [
        {"latitude": lat, "longitude": lon, "magnitude": mag}
        for lat, lon, mag in rows
    ]
    return jsonify(payload)


@app.route("/api/bounds")
def api_bounds():
    lat1 = parse_float("lat1", -30.0)
    lat2 = parse_float("lat2", 30.0)
    lon1 = parse_float("lon1", -60.0)
    lon2 = parse_float("lon2", 60.0)

    lat_min, lat_max = sorted((lat1, lat2))
    lon_min, lon_max = sorted((lon1, lon2))

    rows = get_sqlite_rows_by_bounds(lat_min, lat_max, lon_min, lon_max)
    payload = [
        {"latitude": lat, "longitude": lon, "magnitude": mag}
        for lat, lon, mag in rows
    ]
    return jsonify(payload)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_sqlite_db()
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
else:
    init_sqlite_db()
