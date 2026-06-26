from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import requests

@dataclass
class EarthquakeSource:
    name: str
    display_name: str
    coverage: str
    attribution: str
    homepage_url: str
    supports_realtime: bool = True
    supports_historical: bool = False
    supported_feeds: list[str] = field(default_factory=list)
    enabled_by_default: bool = True

    def fetch(self, feed: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError
    def normalize(self, raw_event: dict[str, Any], feed: str) -> dict[str, Any] | None:
        raise NotImplementedError

def get_json(url: str, timeout: int=15, params: dict[str, Any] | None=None) -> Any:
    r=requests.get(url, timeout=timeout, params=params, headers={'User-Agent':'earthquake-risk-dashboard/1.0'})
    r.raise_for_status(); return r.json()
