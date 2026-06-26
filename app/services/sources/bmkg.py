from __future__ import annotations
from datetime import datetime, timezone
from .base import EarthquakeSource, get_json
from .normalizer import canonical_event, deterministic_id
class BMKGSource(EarthquakeSource):
    def __init__(self): super().__init__('bmkg','BMKG Indonesia','Indonesia','BMKG Indonesia','https://www.bmkg.go.id/',True,False,['latest','felt','m5','tsunami'])
    def fetch(self, feed, params=None):
        url='https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json' if feed in {'latest','tsunami'} else 'https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json'
        payload=get_json(url, int((params or {}).get('timeout',15)))
        gempa=(payload.get('Infogempa') or {}).get('gempa', [])
        if isinstance(gempa, dict): gempa=[gempa]
        return [r for e in gempa if (r:=self.normalize(e, feed))]
    def normalize(self, e, feed):
        coords=str(e.get('Coordinates') or e.get('coordinates') or '').split(',')
        lat=e.get('LintangDecimal') or (coords[0] if len(coords)>=2 else None); lon=e.get('BujurDecimal') or (coords[1] if len(coords)>=2 else None)
        mag=e.get('Magnitude'); depth=str(e.get('Kedalaman') or '').split()[0]
        time_s=' '.join(x for x in [e.get('Tanggal'), e.get('Jam')] if x)
        time_ms=0
        for fmt in ('%d %b %Y %H:%M:%S %Z','%d-%b-%Y %H:%M:%S %Z'):
            try: time_ms=int(datetime.strptime(time_s,fmt).replace(tzinfo=timezone.utc).timestamp()*1000); break
            except Exception: pass
        eid=e.get('EventID') or deterministic_id('bmkg',time_s,lat,lon,mag)
        if not str(eid).startswith('bmkg:'): eid='bmkg:'+str(eid)
        return canonical_event(event_id=eid, source='bmkg', source_feed=feed, time_ms=time_ms, place=e.get('Wilayah') or e.get('Dirasakan'), magnitude=mag, latitude=lat, longitude=lon, depth=depth, tsunami=1 if str(e.get('Potensi','')).lower().find('tsunami')>=0 else 0, url='https://www.bmkg.go.id/gempabumi/', raw_source=e)
