from __future__ import annotations
from typing import Any
from .base import EarthquakeSource, get_json
from .normalizer import canonical_event
class GeoNetSource(EarthquakeSource):
    def __init__(self): super().__init__('geonet','GeoNet New Zealand','New Zealand/Oceania','GeoNet','https://www.geonet.org.nz/',True,True,['latest'])
    def fetch(self, feed, params=None):
        payload=get_json('https://api.geonet.org.nz/quake', int((params or {}).get('timeout',15)))
        return [r for f in payload.get('features',[]) if (r:=self.normalize(f, feed))]
    def normalize(self, f, feed):
        p=f.get('properties') or {}; c=(f.get('geometry') or {}).get('coordinates') or []
        if len(c)<2: return None
        eid=f.get('id') or p.get('publicID') or p.get('id')
        return canonical_event(event_id='geonet:'+str(eid), source='geonet', source_feed=feed, time_ms=p.get('time') or p.get('origintime'), updated_ms=p.get('modificationtime'), place=p.get('locality'), magnitude=p.get('magnitude'), longitude=c[0], latitude=c[1], depth=c[2] if len(c)>2 else p.get('depth'), url='https://www.geonet.org.nz/earthquake/'+str(eid), detail_url=None, raw_source=f)
