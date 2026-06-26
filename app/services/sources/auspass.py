from .base import EarthquakeSource
class AusPassSource(EarthquakeSource):
    def __init__(self): super().__init__('auspass','AusPass FDSN','Australia/Oceania','AusPass','https://auspass.edu.au/',False,True,['latest'],False)
    def fetch(self, feed, params=None): return []
    def normalize(self, raw_event, feed): return None
