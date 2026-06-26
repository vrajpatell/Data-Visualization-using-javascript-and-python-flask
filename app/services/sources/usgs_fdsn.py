from __future__ import annotations
from typing import Any
from .base import EarthquakeSource, get_json
from .usgs_geojson import USGSGeoJSONSource
class USGSFDSNSource(EarthquakeSource):
    def __init__(self): super().__init__('usgs_fdsn','USGS FDSN Event API','Global','USGS Earthquake Hazards Program','https://earthquake.usgs.gov/fdsnws/event/1/',True,True,['latest','day','7day','30day'])
    def fetch(self, feed, params=None):
        p=dict(params or {}); p.setdefault('format','geojson'); p.setdefault('limit', p.get('limit', 1000));
        p={k:v for k,v in p.items() if k in {'format','starttime','endtime','minmagnitude','maxmagnitude','mindepth','maxdepth','latitude','longitude','maxradiuskm','minlatitude','maxlatitude','minlongitude','maxlongitude','limit','orderby'} and v not in (None,'')}
        payload=get_json('https://earthquake.usgs.gov/fdsnws/event/1/query', int((params or {}).get('timeout',15)), p)
        parser=USGSGeoJSONSource(); rows=[]
        for f in payload.get('features',[]):
            row=parser.normalize(f, feed)
            if row: row['id']=row['id'].replace('usgs:','usgs_fdsn:',1); row['source']='usgs_fdsn'; rows.append(row)
        return rows
    def normalize(self, raw_event, feed): return USGSGeoJSONSource().normalize(raw_event, feed)
