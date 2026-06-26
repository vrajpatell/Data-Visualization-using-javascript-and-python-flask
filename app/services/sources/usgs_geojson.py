from __future__ import annotations
from typing import Any
from .base import EarthquakeSource, get_json
from .normalizer import canonical_event
FEEDS={'hour':'all_hour.geojson','day':'all_day.geojson','7day':'all_week.geojson','30day':'all_month.geojson','significant':'significant_month.geojson','m1':'1.0_month.geojson','m2.5':'2.5_month.geojson','m4.5':'4.5_month.geojson'}
class USGSGeoJSONSource(EarthquakeSource):
    def __init__(self): super().__init__('usgs_geojson','USGS GeoJSON','Global','USGS Earthquake Hazards Program','https://earthquake.usgs.gov/',True,False,list(FEEDS))
    def fetch(self, feed, params=None):
        payload=get_json('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/'+FEEDS.get(feed,FEEDS['day']), int((params or {}).get('timeout',15)))
        return [self.normalize(f, feed) for f in payload.get('features',[]) if self.normalize(f, feed)]
    def normalize(self, f: dict[str,Any], feed: str):
        props=f.get('properties') or {}; coords=(f.get('geometry') or {}).get('coordinates') or []
        if len(coords)<2 or not f.get('id'): return None
        return canonical_event(event_id='usgs:'+str(f.get('id')), source='usgs', source_feed=feed, time_ms=props.get('time'), updated_ms=props.get('updated'), place=props.get('place'), magnitude=props.get('mag'), longitude=coords[0], latitude=coords[1], depth=coords[2] if len(coords)>2 else None, alert=props.get('alert'), tsunami=props.get('tsunami'), significance=props.get('sig'), felt=props.get('felt'), url=props.get('url'), detail_url=props.get('detail'), event_type=props.get('type'), raw_source=f, network=props.get('net'), code=props.get('code'), mag_type=props.get('magType'), cdi=props.get('cdi'), mmi=props.get('mmi'), status=props.get('status'), gap=props.get('gap'), dmin=props.get('dmin'), rms=props.get('rms'), nst=props.get('nst'))
