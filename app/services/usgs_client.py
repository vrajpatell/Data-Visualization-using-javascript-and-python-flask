from __future__ import annotations
import logging
from typing import Any
from app.utils import rough_region, safe_float
log=logging.getLogger(__name__)

def parse_geojson_features(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
        raise ValueError('Invalid USGS GeoJSON payload')
    rows=[]
    for f in payload.get('features', []):
        if not isinstance(f, dict): continue
        props=f.get('properties') or {}; geom=f.get('geometry') or {}; coords=geom.get('coordinates') or []
        if len(coords) < 2 or f.get('id') is None: continue
        lon=safe_float(coords[0]); lat=safe_float(coords[1]); depth=safe_float(coords[2] if len(coords)>2 else 0, 0.0); mag=safe_float(props.get('mag'))
        if lon is None or lat is None or mag is None or not (-180<=lon<=180) or not (-90<=lat<=90): continue
        place=str(props.get('place') or 'Unknown')
        row={
            'id': str(f.get('id')), 'time_ms': int(props.get('time') or 0), 'updated_ms': int(props.get('updated') or 0),
            'place': place, 'magnitude': float(mag), 'longitude': float(lon), 'latitude': float(lat), 'depth': float(depth or 0),
            'alert': props.get('alert'), 'tsunami': int(props.get('tsunami') or 0), 'significance': props.get('sig'), 'felt': props.get('felt'),
            'cdi': props.get('cdi'), 'mmi': props.get('mmi'), 'status': props.get('status'), 'event_type': props.get('type'),
            'network': props.get('net'), 'code': props.get('code'), 'url': props.get('url'), 'detail_url': props.get('detail'),
            'mag_type': props.get('magType'), 'gap': props.get('gap'), 'dmin': props.get('dmin'), 'rms': props.get('rms'), 'nst': props.get('nst'),
        }
        row['region']=rough_region(row['latitude'], row['longitude'], place)
        rows.append(row)
    return rows

def fetch_feed(url: str, timeout: int=15) -> list[dict[str, Any]]:
    try:
        import requests
        resp=requests.get(url, timeout=timeout, headers={'User-Agent':'earthquake-risk-dashboard/1.0'})
        resp.raise_for_status()
        return parse_geojson_features(resp.json())
    except ImportError:
        import json
        from urllib.request import Request, urlopen
        req=Request(url, headers={'User-Agent':'earthquake-risk-dashboard/1.0'})
        with urlopen(req, timeout=timeout) as resp:
            return parse_geojson_features(json.loads(resp.read().decode('utf-8')))
