from __future__ import annotations
import time
from flask import Blueprint, current_app, jsonify, render_template, request
from app.services import analytics, model
from app.services.cache import all_meta, all_records, connect, count_records, feed_meta_key, query_earthquakes, seed_bootstrap_if_empty, set_meta, upsert_earthquakes
from app.services.usgs_client import fetch_feed
from app.utils import bool_arg, parse_time_ms, safe_float, safe_int
bp=Blueprint('main',__name__)

def feed_url(name):
    feeds=current_app.config['FEEDS']; return current_app.config['USGS_FEED_URL'] if name=='custom' else feeds.get(name, feeds.get(current_app.config['DEFAULT_FEED_WINDOW'], current_app.config['USGS_FEED_URL']))
def feed_meta_value(meta, key, feed, default=''):
    scoped=feed_meta_key(key,feed)
    if scoped in meta: return meta[scoped]
    return meta.get(key, default) if meta.get('last_refresh_source') == feed else default

def refresh_if_needed(feed='day', force=False):
    db=current_app.config['SQLITE_DB_PATH']; ttl=current_app.config['CACHE_TTL_SECONDS']; meta=all_meta(db)
    last=int(feed_meta_value(meta,'last_successful_refresh_epoch',feed,'0') or 0)
    if not force and int(time.time())-last <= ttl: return 'cache'
    try:
        rows=fetch_feed(feed_url(feed), current_app.config['REQUEST_TIMEOUT_SECONDS']); n=upsert_earthquakes(db,rows,feed,False)
        return f'live:{n}'
    except Exception as exc:
        current_app.logger.warning('USGS refresh failed: %s', exc)
        with connect(db) as c:
            set_meta(c,'last_refresh_error',str(exc)[:300]); set_meta(c,'last_refresh_source','fallback_cache')
            set_meta(c,feed_meta_key('last_refresh_error',feed),str(exc)[:300]); set_meta(c,feed_meta_key('last_refresh_source',feed),'fallback_cache')
            c.commit()
        if count_records(db)==0: seed_bootstrap_if_empty(db, current_app.config['ENABLE_BOOTSTRAP_DATA']); return 'bootstrap_fallback'
        return 'fallback_cache'
def filters_from_args():
    mag_min=safe_float(request.args.get('mag_min'),0.0); mag_max=safe_float(request.args.get('mag_max'),10.0)
    lat1=safe_float(request.args.get('lat1'),-90.0); lat2=safe_float(request.args.get('lat2'),90.0); lon1=safe_float(request.args.get('lon1'),-180.0); lon2=safe_float(request.args.get('lon2'),180.0)
    mag_min,mag_max=sorted((mag_min,mag_max)); lat1=max(-90,min(90,lat1)); lat2=max(-90,min(90,lat2)); lon1=max(-180,min(180,lon1)); lon2=max(-180,min(180,lon2)); lat_min,lat_max=sorted((lat1,lat2)); lon_min,lon_max=sorted((lon1,lon2))
    return {'mag_min':mag_min,'mag_max':mag_max,'lat_min':lat_min,'lat_max':lat_max,'lon_min':lon_min,'lon_max':lon_max,'start_time':parse_time_ms(request.args.get('start_time')),'end_time':parse_time_ms(request.args.get('end_time'))}
@bp.route('/')
@bp.route('/dashboard')
def dashboard(): return render_template('dashboard.html')
@bp.route('/globe')
def globe(): return render_template('globe.html')
@bp.route('/map')
def map_page(): return render_template('map.html')
@bp.route('/forecast')
def forecast_page(): return render_template('forecast.html')
@bp.route('/about')
def about(): return render_template('about.html')
@bp.route('/api/earthquakes')
def api_earthquakes():
    feed=request.args.get('feed', current_app.config['DEFAULT_FEED_WINDOW']); refresh=refresh_if_needed(feed,bool_arg('refresh'))
    limit=safe_int(request.args.get('limit'),500,1,current_app.config['MAX_API_LIMIT']); sort=request.args.get('sort','time_desc')
    filt=filters_from_args(); rows=query_earthquakes(current_app.config['SQLITE_DB_PATH'],filt,limit,sort); meta=all_meta(current_app.config['SQLITE_DB_PATH'])
    warnings=[]
    source=feed_meta_value(meta,'last_refresh_source',feed,'cache')
    last_epoch=int(feed_meta_value(meta,'last_successful_refresh_epoch',feed,'0') or 0)
    if 'fallback' in refresh or source in {'bootstrap_demo','fallback_cache'}: warnings.append('Using cached or bootstrap data because live USGS refresh was unavailable or skipped.')
    return jsonify({'meta':{'source':source,'refresh_result':refresh,'last_refresh_epoch':last_epoch,'count':len(rows),'available_feeds':list(current_app.config['FEEDS'].keys())},'filters':filt,'count':len(rows),'source':source,'warnings':warnings,'data':rows})
@bp.route('/api/summary')
def api_summary():
    refresh_if_needed(request.args.get('feed', current_app.config['DEFAULT_FEED_WINDOW']), False)
    rows=query_earthquakes(current_app.config['SQLITE_DB_PATH'],filters_from_args(),current_app.config['MAX_API_LIMIT'],'time_desc')
    feed=request.args.get('feed', current_app.config['DEFAULT_FEED_WINDOW']); meta=all_meta(current_app.config['SQLITE_DB_PATH'])
    return jsonify({'summary':analytics.summarize(rows),'count':len(rows),'source':feed_meta_value(meta,'last_refresh_source',feed,'cache')})
@bp.route('/api/regions')
def api_regions(): return jsonify({'regions':analytics.regions(query_earthquakes(current_app.config['SQLITE_DB_PATH'],filters_from_args(),current_app.config['MAX_API_LIMIT'],'time_desc'))})
@bp.route('/api/timeseries')
def api_timeseries(): return jsonify({'interval':request.args.get('interval','hour'),'series':analytics.timeseries(query_earthquakes(current_app.config['SQLITE_DB_PATH'],filters_from_args(),current_app.config['MAX_API_LIMIT'],'time_desc'), request.args.get('interval','hour'))})
@bp.route('/api/forecast')
def api_forecast():
    lat=safe_float(request.args.get('lat'),37.7749); lon=safe_float(request.args.get('lon'),-122.4194); radius=safe_float(request.args.get('radius_km'),300); hours=safe_int(request.args.get('hours'),72,1,24*30); minmag=safe_float(request.args.get('min_magnitude'),2.5)
    rows=all_records(current_app.config['SQLITE_DB_PATH'], current_app.config['MAX_API_LIMIT']); return jsonify(model.predict(rows,current_app.config['MODEL_PATH'],lat,lon,radius,hours,minmag))
@bp.route('/api/model/train', methods=['POST'])
def api_train():
    token=current_app.config.get('ADMIN_TOKEN')
    if not token or request.headers.get('X-Admin-Token') != token: return jsonify({'error':'training endpoint disabled or unauthorized'}), 403
    return jsonify(model.train(all_records(current_app.config['SQLITE_DB_PATH'],20000), current_app.config['MODEL_PATH']))
@bp.route('/api/model/status')
def api_model_status(): return jsonify(model.status(current_app.config['MODEL_PATH']))
@bp.route('/health')
def health(): return jsonify({'status':'ok'})
@bp.route('/api/health/deep')
def deep_health():
    db=current_app.config['SQLITE_DB_PATH']; meta=all_meta(db); ok=True
    try: records=count_records(db)
    except Exception: ok=False; records=0
    st=model.status(current_app.config['MODEL_PATH'])
    return jsonify({'app':'ok','database_ok':ok,'cache_ok':records>=0,'model_ok':st['model_exists'],'last_refresh':meta.get('last_successful_refresh_epoch'),'record_count':records,'model':st})
