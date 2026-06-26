from __future__ import annotations
from flask import current_app
from .usgs_geojson import USGSGeoJSONSource
from .usgs_fdsn import USGSFDSNSource
from .emsc import EMSCSource
from .isc import ISCSource
from .geofon import GEOFONSource
from .bmkg import BMKGSource
from .geonet import GeoNetSource
from .auspass import AusPassSource
SOURCE_REGISTRY={'usgs':USGSGeoJSONSource(),'usgs_geojson':USGSGeoJSONSource(),'usgs_fdsn':USGSFDSNSource(),'emsc':EMSCSource(),'isc':ISCSource(),'geofon':GEOFONSource(),'bmkg':BMKGSource(),'geonet':GeoNetSource(),'auspass':AusPassSource()}
def enabled_source_names():
    raw=current_app.config.get('ENABLED_SOURCES','usgs_geojson')
    names=[s.strip() for s in raw.split(',') if s.strip()]
    if not current_app.config.get('SOURCE_ENABLE_AUSPASS') and 'auspass' in names: names.remove('auspass')
    return [n for n in names if n in SOURCE_REGISTRY]
def resolve_sources(requested: str):
    if requested in ('all',''): return [SOURCE_REGISTRY[n] for n in enabled_source_names()]
    if requested=='usgs': requested='usgs_geojson'
    return [SOURCE_REGISTRY[requested]] if requested in SOURCE_REGISTRY else [SOURCE_REGISTRY['usgs_geojson']]
