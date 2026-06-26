import os
import pytest

SAMPLE={"type":"FeatureCollection","features":[{"type":"Feature","id":"abc","properties":{"mag":2.7,"place":"10 km S of Test, California","time":1700000000000,"updated":1700000001000,"sig":110,"tsunami":0,"net":"us","code":"abc","type":"earthquake"},"geometry":{"type":"Point","coordinates":[-122.1,37.2,8.5]}}]}

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path/'test.db'))
    monkeypatch.setenv('ENABLE_BOOTSTRAP_DATA','false')
    from app import create_app
    app=create_app(); app.config['TESTING']=True
    from app.services.cache import upsert_earthquakes
    from app.services.usgs_client import parse_geojson_features
    upsert_earthquakes(app.config['SQLITE_DB_PATH'], parse_geojson_features(SAMPLE), 'day')
    return app.test_client()

def test_geojson_parsing():
    from app.services.usgs_client import parse_geojson_features
    rows=parse_geojson_features(SAMPLE)
    assert rows[0]['id']=='abc'
    assert rows[0]['magnitude']==2.7
    assert rows[0]['latitude']==37.2
    assert rows[0]['region']=='California'

def test_invalid_geojson():
    from app.services.usgs_client import parse_geojson_features
    with pytest.raises(ValueError): parse_geojson_features({'bad': []})

def test_cache_upsert(tmp_path):
    from app.services.cache import init_db, upsert_earthquakes, count_records
    db=str(tmp_path/'x.db'); init_db(db)
    row={'id':'1','time_ms':1,'updated_ms':1,'place':'A','magnitude':1.0,'longitude':1,'latitude':1,'depth':2}
    upsert_earthquakes(db,[row],'test'); row['magnitude']=3.0; upsert_earthquakes(db,[row],'test')
    assert count_records(db)==1

def test_health(client): assert client.get('/health').json['status']=='ok'
def test_earthquakes_api(client):
    r=client.get('/api/earthquakes?mag_min=1&limit=5')
    assert r.status_code==200 and r.json['count']>=1 and isinstance(r.json['data'], list)
def test_query_param_parsing(client):
    r=client.get('/api/earthquakes?mag_min=bad&lat1=99&limit=999999')
    assert r.status_code==200
    assert r.json['filters']['lat_max'] == 90

def test_summary(client):
    r=client.get('/api/summary')
    assert r.status_code==200 and 'total_events' in r.json['summary']

def test_forecast_fallback(client):
    r=client.get('/api/forecast?lat=37.2&lon=-122.1&radius_km=50')
    assert r.status_code==200 and 'risk_score' in r.json and 'does not predict exact' in r.json['warning']

def test_model_status(client):
    r=client.get('/api/model/status')
    assert r.status_code==200 and 'model_exists' in r.json


def test_refresh_metadata_is_per_feed(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path/'feeds.db'))
    monkeypatch.setenv('ENABLE_BOOTSTRAP_DATA','false')
    from app import create_app
    from app import routes
    from app.services.cache import all_meta

    app=create_app(); app.config['TESTING']=True; app.config['CACHE_TTL_SECONDS']=3600
    calls=[]
    def fake_fetch(url, timeout):
        calls.append(url)
        idx=len(calls)
        return [{'id':f'event-{idx}','time_ms':idx,'updated_ms':idx,'place':'Test','magnitude':1.0,'longitude':1,'latitude':1,'depth':1}]
    monkeypatch.setattr(routes, 'fetch_feed', fake_fetch)

    feeds=['day','7day','30day','significant','m1','m2.5','m4.5']
    with app.app_context():
        for feed in feeds:
            assert routes.refresh_if_needed(feed) == 'live:1'
            assert routes.refresh_if_needed(feed) == 'cache'

    assert len(calls) == len(feeds)
    meta=all_meta(app.config['SQLITE_DB_PATH'])
    for feed in feeds:
        assert int(meta[f'last_successful_refresh_epoch:{feed}']) > 0
        assert meta[f'last_refresh_source:{feed}'] == feed


def test_legacy_global_metadata_only_applies_to_matching_feed(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path/'legacy.db'))
    monkeypatch.setenv('ENABLE_BOOTSTRAP_DATA','false')
    from app import create_app
    from app import routes
    from app.services.cache import connect, set_meta
    import time

    app=create_app(); app.config['TESTING']=True; app.config['CACHE_TTL_SECONDS']=3600
    with connect(app.config['SQLITE_DB_PATH']) as c:
        set_meta(c, 'last_successful_refresh_epoch', int(time.time()))
        set_meta(c, 'last_refresh_source', 'day')
        c.commit()

    calls=[]
    def fake_fetch(url, timeout):
        calls.append(url)
        return [{'id':'legacy-7day','time_ms':1,'updated_ms':1,'place':'Test','magnitude':1.0,'longitude':1,'latitude':1,'depth':1}]
    monkeypatch.setattr(routes, 'fetch_feed', fake_fetch)

    with app.app_context():
        assert routes.refresh_if_needed('day') == 'cache'
        assert routes.refresh_if_needed('7day') == 'live:1'

    assert len(calls) == 1


def test_earthquakes_api_refreshes_each_feed_independently(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path/'api-feeds.db'))
    monkeypatch.setenv('ENABLE_BOOTSTRAP_DATA','false')
    from app import create_app
    from app import routes

    app=create_app(); app.config['TESTING']=True; app.config['CACHE_TTL_SECONDS']=3600
    calls=[]
    def fake_fetch(url, timeout):
        calls.append(url)
        idx=len(calls)
        return [{'id':f'api-event-{idx}','time_ms':idx,'updated_ms':idx,'place':'Test','magnitude':1.0,'longitude':1,'latitude':1,'depth':1}]
    monkeypatch.setattr(routes, 'fetch_feed', fake_fetch)

    client=app.test_client()
    feeds=['day','7day','30day','significant','m1','m2.5','m4.5']
    for feed in feeds:
        first=client.get(f'/api/earthquakes?feed={feed}&limit=1')
        second=client.get(f'/api/earthquakes?feed={feed}&limit=1')
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json['meta']['refresh_result'] == 'live:1'
        assert second.json['meta']['refresh_result'] == 'cache'
        assert first.json['meta']['source'] == feed

    assert len(calls) == len(feeds)

def test_normalizers_and_source_adapters_reject_bad_coordinates():
    from app.services.sources.normalizer import validate_latitude, validate_longitude, validate_event_coordinates
    from app.services.sources.usgs_geojson import USGSGeoJSONSource
    from app.services.sources.bmkg import BMKGSource
    from app.services.sources.geonet import GeoNetSource
    import math
    assert not validate_latitude(math.nan)
    assert not validate_longitude(math.inf)
    assert not validate_event_coordinates({'latitude': 130, 'longitude': 45})
    usgs=USGSGeoJSONSource().normalize(SAMPLE['features'][0], 'day')
    assert usgs['latitude'] == 37.2 and usgs['longitude'] == -122.1 and usgs['id'].startswith('usgs:')
    assert USGSGeoJSONSource().normalize({'id':'bad','properties':{'mag':1},'geometry':{'coordinates':[130,95,1]}}, 'day') is None
    bmkg=BMKGSource().normalize({'Coordinates':'-6.12,130.42','Magnitude':'4.8','Kedalaman':'42 km','Wilayah':'Indonesia'}, 'latest')
    assert bmkg['latitude'] == -6.12 and bmkg['longitude'] == 130.42
    geonet=GeoNetSource().normalize({'id':'nz1','properties':{'magnitude':3,'locality':'NZ','time':1700000000000},'geometry':{'coordinates':[174.7,-41.2,12]}}, 'latest')
    assert geonet['latitude'] == -41.2 and geonet['longitude'] == 174.7

def test_source_feed_demo_and_antimeridian_filters(tmp_path):
    from app.services.cache import init_db, upsert_earthquakes, query_earthquakes
    db=str(tmp_path/'filters.db'); init_db(db)
    upsert_earthquakes(db,[{'id':'usgs:day','source':'usgs','time_ms':1,'updated_ms':1,'place':'A','magnitude':2,'longitude':175,'latitude':10,'depth':1}], 'day')
    upsert_earthquakes(db,[{'id':'usgs:month','source':'usgs','time_ms':2,'updated_ms':2,'place':'B','magnitude':3,'longitude':-175,'latitude':-10,'depth':1}], '30day')
    upsert_earthquakes(db,[{'id':'emsc:x','source':'emsc','time_ms':3,'updated_ms':3,'place':'C','magnitude':4,'longitude':0,'latitude':0,'depth':1}], 'day')
    upsert_earthquakes(db,[{'id':'bootstrap-x','source':'bootstrap_demo','time_ms':4,'updated_ms':4,'place':'Demo','magnitude':5,'longitude':50,'latitude':5,'depth':1}], 'bootstrap_demo', True)
    assert [r['id'] for r in query_earthquakes(db, {'source':'usgs','source_feed':'day','include_demo':False}, 10)] == ['usgs:day']
    assert [r['id'] for r in query_earthquakes(db, {'source':'usgs','source_feed':'30day','include_demo':False}, 10)] == ['usgs:month']
    assert all(not r['is_bootstrap'] for r in query_earthquakes(db, {'source':'all','include_demo':False}, 10))
    assert any(r['is_bootstrap'] for r in query_earthquakes(db, {'source':'all','include_demo':True}, 10))
    ids={r['id'] for r in query_earthquakes(db, {'lon1':170,'lon2':-170,'include_demo':False}, 10)}
    assert {'usgs:day','usgs:month'} <= ids and 'emsc:x' not in ids
    assert [r['id'] for r in query_earthquakes(db, {'lon1':-10,'lon2':10,'include_demo':False}, 10)] == ['emsc:x']

def test_sources_and_filtered_api(client):
    assert client.get('/api/sources').status_code == 200
    assert client.get('/api/regions?source=usgs&feed=day').status_code == 200
    assert client.get('/api/timeseries?source=usgs&feed=day').status_code == 200
    r=client.get('/api/earthquakes?source=usgs&feed=day&include_demo=false')
    assert r.status_code == 200 and r.json['meta']['demo_count'] == 0
