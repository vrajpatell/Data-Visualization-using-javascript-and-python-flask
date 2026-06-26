from .base import EarthquakeSource
class GEOFONSource(EarthquakeSource):
    def __init__(self): super().__init__('geofon','GFZ/GEOFON','Global/Europe','GFZ GEOFON','https://geofon.gfz-potsdam.de/',True,True,['latest','day','7day','30day'])
    def fetch(self, feed, params=None): return []
    def normalize(self, raw_event, feed): return None
