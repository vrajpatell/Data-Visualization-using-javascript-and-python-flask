from .usgs_fdsn import USGSFDSNSource
class EMSCSource(USGSFDSNSource):
    def __init__(self): super().__init__(); self.name='emsc'; self.display_name='EMSC / SeismicPortal'; self.coverage='Europe/global'; self.attribution='EMSC / SeismicPortal (CC BY 4.0 where applicable)'; self.homepage_url='https://www.seismicportal.eu/'; self.supported_feeds=['latest','day','7day','30day']
