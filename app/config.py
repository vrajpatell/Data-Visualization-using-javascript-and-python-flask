import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-not-secret')
    USGS_FEED_URL = os.getenv('USGS_FEED_URL', 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson')
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '300'))
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', str(BASE_DIR / 'data' / 'earthquakes.db'))
    DEFAULT_FEED_WINDOW = os.getenv('DEFAULT_FEED_WINDOW', 'day')
    MODEL_PATH = os.getenv('MODEL_PATH', str(BASE_DIR / 'models' / 'earthquake_risk.joblib'))
    ENABLE_BOOTSTRAP_DATA = os.getenv('ENABLE_BOOTSTRAP_DATA', 'false').lower() in {'1','true','yes','on'}
    ALLOW_BOOTSTRAP_AS_FRESH_CACHE = os.getenv('ALLOW_BOOTSTRAP_AS_FRESH_CACHE', 'false').lower() in {'1','true','yes','on'}
    ENABLE_MODEL_TRAINING_ON_STARTUP = os.getenv('ENABLE_MODEL_TRAINING_ON_STARTUP', 'false').lower() in {'1','true','yes','on'}
    MAX_API_LIMIT = int(os.getenv('MAX_API_LIMIT', '2000'))
    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
    FLASK_ENV = os.getenv('FLASK_ENV', os.getenv('ENV', 'production'))
    REQUEST_TIMEOUT_SECONDS = int(os.getenv('REQUEST_TIMEOUT_SECONDS', '15'))
    SOURCE_TIMEOUT_SECONDS = int(os.getenv('SOURCE_TIMEOUT_SECONDS', os.getenv('REQUEST_TIMEOUT_SECONDS', '15')))
    SOURCE_MAX_RETRIES = int(os.getenv('SOURCE_MAX_RETRIES', '2'))
    SOURCE_REFRESH_TTL_SECONDS = int(os.getenv('SOURCE_REFRESH_TTL_SECONDS', os.getenv('CACHE_TTL_SECONDS', '300')))
    SOURCE_BMKG_RATE_LIMIT_PER_MINUTE = int(os.getenv('SOURCE_BMKG_RATE_LIMIT_PER_MINUTE', '60'))
    SOURCE_ENABLE_AUSPASS = os.getenv('SOURCE_ENABLE_AUSPASS', 'false').lower() in {'1','true','yes','on'}
    SOURCE_ENABLE_EXPERIMENTAL = os.getenv('SOURCE_ENABLE_EXPERIMENTAL', 'false').lower() in {'1','true','yes','on'}
    ENABLED_SOURCES = os.getenv('ENABLED_SOURCES', 'usgs_geojson,usgs_fdsn,emsc,isc,geofon,bmkg,geonet')

    FEEDS = {
        'hour': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson',
        'day': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson',
        '7day': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson',
        '30day': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson',
        'significant': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson',
        'm1': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/1.0_month.geojson',
        'm2.5': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson',
        'm4.5': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson',
    }
