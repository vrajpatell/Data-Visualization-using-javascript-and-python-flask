from .base import EarthquakeSource
class ISCSource(EarthquakeSource):
    def __init__(self): super().__init__('isc','ISC FDSN','Global reviewed catalogue','International Seismological Centre','https://www.isc.ac.uk/',False,True,['latest','day','7day','30day'])
    def fetch(self, feed, params=None): return []
    def normalize(self, raw_event, feed): return None
