from __future__ import annotations
import math, hashlib, json
from typing import Any
from app.utils import safe_float, rough_region

def _finite(v):
    try: return math.isfinite(float(v))
    except (TypeError, ValueError): return False

def validate_latitude(lat: Any) -> bool:
    return _finite(lat) and -90 <= float(lat) <= 90

def validate_longitude(lon: Any) -> bool:
    return _finite(lon) and -180 <= float(lon) <= 180

def normalize_lat_lon(lat: Any, lon: Any) -> tuple[float, float] | None:
    if not validate_latitude(lat) or not validate_longitude(lon): return None
    return float(lat), float(lon)

def validate_event_coordinates(event: dict[str, Any]) -> bool:
    return validate_latitude(event.get('latitude')) and validate_longitude(event.get('longitude'))

def deterministic_id(prefix: str, *parts: Any) -> str:
    payload='|'.join(str(p) for p in parts)
    return f"{prefix}:{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:16]}"

def canonical_event(*, event_id: str, source: str, source_feed: str, time_ms: Any, updated_ms: Any=None,
                    place: str='Unknown', magnitude: Any=None, latitude: Any=None, longitude: Any=None,
                    depth: Any=None, alert=None, tsunami: Any=0, significance=None, felt=None, url=None,
                    detail_url=None, event_type: str='earthquake', raw_source: dict[str, Any] | None=None,
                    **extra) -> dict[str, Any] | None:
    latlon=normalize_lat_lon(latitude, longitude)
    mag=safe_float(magnitude)
    if latlon is None or mag is None: return None
    lat, lon=latlon
    dep=safe_float(depth)
    row={
        'id': event_id, 'source': source, 'source_feed': source_feed,
        'time_ms': int(time_ms or 0), 'updated_ms': int(updated_ms or time_ms or 0),
        'place': str(place or 'Unknown'), 'magnitude': float(mag), 'latitude': lat, 'longitude': lon,
        'depth': None if dep is None else float(dep), 'alert': alert, 'tsunami': int(tsunami or 0),
        'significance': significance, 'felt': felt, 'url': url, 'detail_url': detail_url,
        'event_type': event_type or 'earthquake', 'raw_source': raw_source or {},
    }
    row.update(extra)
    row['region']=rough_region(lat, lon, row['place'])
    return row
