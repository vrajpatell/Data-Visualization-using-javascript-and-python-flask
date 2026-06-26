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
    upsert_earthquakes(app.config['SQLITE_DB_PATH'], parse_geojson_features(SAMPLE), 'test')
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
