from __future__ import annotations
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any
from flask import request

DISCLAIMER = ('Experimental probabilistic seismic activity forecast only. This app does not predict exact earthquake times, locations, or magnitudes; use official emergency sources for safety decisions.')

def utc_now_ms() -> int: return int(datetime.now(timezone.utc).timestamp()*1000)
def iso_from_ms(ms: int | None) -> str | None:
    if not ms: return None
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc).isoformat()
def parse_time_ms(value: str | None) -> int | None:
    if not value: return None
    try:
        if value.isdigit():
            v=int(value); return v if v>10_000_000_000 else v*1000
        return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()*1000)
    except Exception: return None

def safe_float(v: Any, default: float | None=None) -> float | None:
    try:
        if v is None or v == '': return default
        f=float(v)
        return f if f == f and abs(f) != float('inf') else default
    except Exception: return default

def safe_int(v: Any, default: int=0, lo: int | None=None, hi: int | None=None) -> int:
    try: n=int(v)
    except Exception: n=default
    if lo is not None: n=max(lo,n)
    if hi is not None: n=min(hi,n)
    return n

def bool_arg(name: str, default: bool=False) -> bool:
    raw=request.args.get(name)
    if raw is None: return default
    return raw.lower() in {'1','true','yes','on'}

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r=6371.0; p1,p2=radians(lat1),radians(lat2); dp=radians(lat2-lat1); dl=radians(lon2-lon1)
    a=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*r*asin(sqrt(a))

def rough_region(lat: float | None, lon: float | None, place: str='') -> str:
    if place and ',' in place: return place.split(',')[-1].strip()[:80]
    if lat is None or lon is None: return 'Unknown'
    ns='Northern' if lat>=0 else 'Southern'; ew='Eastern' if lon>=0 else 'Western'
    return f'{ns} {ew} Hemisphere'
