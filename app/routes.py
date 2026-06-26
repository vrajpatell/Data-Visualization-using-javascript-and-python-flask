from __future__ import annotations
import time
from flask import Blueprint, current_app, jsonify, render_template, request
from app.services import analytics, model
from app.services.cache import all_meta, all_records, connect, count_records, feed_meta_key, query_earthquakes, seed_bootstrap_if_empty, set_meta, upsert_earthquakes
from app.services.sources import SOURCE_REGISTRY, enabled_source_names, resolve_sources
from app.services.usgs_client import fetch_feed
from app.utils import bool_arg, parse_time_ms, safe_float, safe_int
bp=Blueprint('main',__name__)

def feed_url(name):
    feeds=current_app.config['FEEDS']
    return current_app.config['USGS_FEED_URL'] if name=='custom' else feeds.get(name, feeds.get(current_app.config['DEFAULT_FEED_WINDOW'], current_app.config['USGS_FEED_URL']))

def feed_meta_value(meta, key, feed, source='usgs', default=''):
    keys=[feed_meta_key(key,feed,source), f'{key}:{feed}']
    for k in keys:
        if k in meta: return meta[k]
    return meta.get(key, default) if meta.get('last_refresh_source') == feed else default

def source_params_from_request():
    return {'timeout': current_app.config['SOURCE_TIMEOUT_SECONDS'], 'limit': request.args.get('limit'),
            'minmagnitude': request.args.get('min_magnitude') or request.args.get('mag_min'),
            'maxmagnitude': request.args.get('max_magnitude') or request.args.get('mag_max'),
            'starttime': request.args.get('start_time'), 'endtime': request.args.get('end_time'),
            'minlatitude': request.args.get('lat1'), 'maxlatitude': request.args.get('lat2'),
            'minlongitude': request.args.get('lon1'), 'maxlongitude': request.args.get('lon2'),
            'latitude': request.args.get('lat'), 'longitude': request.args.get('lon'),
            'maxradiuskm': request.args.get('radius_km')}

def refresh_if_needed(feed='day', force=False, source='usgs'):
    db=current_app.config['SQLITE_DB_PATH']; ttl=current_app.config.get('SOURCE_REFRESH_TTL_SECONDS', current_app.config['CACHE_TTL_SECONDS']); meta=all_meta(db)
    sources=resolve_sources(source)
    results=[]
    for src in sources:
        last=int(feed_meta_value(meta,'last_successful_refresh_epoch',feed,src.name,'0') or 0)
        last_source=feed_meta_value(meta,'last_refresh_source',feed,src.name,'')
        local_force=force or (last_source=='bootstrap_demo' and not current_app.config['ALLOW_BOOTSTRAP_AS_FRESH_CACHE'])
        if not local_force and int(time.time())-last <= ttl:
            results.append('cache'); continue
        try:
            rows=fetch_feed(feed_url(feed), current_app.config['REQUEST_TIMEOUT_SECONDS']) if src.name == 'usgs_geojson' else src.fetch(feed, source_params_from_request() if request else {'timeout': current_app.config['SOURCE_TIMEOUT_SECONDS']})
            n=upsert_earthquakes(db, rows, feed, False)
            results.append(f'live:{n}' if src.name == 'usgs_geojson' and source in {'usgs','usgs_geojson'} else f'live:{src.name}:{n}')
        except Exception as exc:
            current_app.logger.warning('%s refresh failed: %s', src.name, exc)
            with connect(db) as c:
                set_meta(c,feed_meta_key('last_refresh_error',feed,src.name),str(exc)[:300]); set_meta(c,feed_meta_key('last_refresh_source',feed,src.name),'fallback_cache'); c.commit()
            results.append('fallback_cache')
    if results and all(r=='cache' for r in results): return 'cache'
    if count_records(db)==0:
        seed_bootstrap_if_empty(db, current_app.config['ENABLE_BOOTSTRAP_DATA']); return 'bootstrap_fallback'
    return ','.join(results or ['cache'])

def filters_from_args():
    mag_min=safe_float(request.args.get('mag_min') or request.args.get('min_magnitude'),0.0); mag_max=safe_float(request.args.get('mag_max') or request.args.get('max_magnitude'),10.0)
    lat1=safe_float(request.args.get('lat1'),-90.0); lat2=safe_float(request.args.get('lat2'),90.0); lon1=safe_float(request.args.get('lon1'),-180.0); lon2=safe_float(request.args.get('lon2'),180.0)
    mag_min,mag_max=sorted((mag_min,mag_max)); lat1=max(-90,min(90,lat1)); lat2=max(-90,min(90,lat2)); lon1=max(-180,min(180,lon1)); lon2=max(-180,min(180,lon2)); lat_min,lat_max=sorted((lat1,lat2))
    crosses=lon1 > lon2
    return {'mag_min':mag_min,'mag_max':mag_max,'lat_min':lat_min,'lat_max':lat_max,'lon1':lon1,'lon2':lon2,'crosses_antimeridian':crosses,'start_time':parse_time_ms(request.args.get('start_time')),'end_time':parse_time_ms(request.args.get('end_time')),'source':request.args.get('source','usgs'),'source_feed':request.args.get('feed', current_app.config['DEFAULT_FEED_WINDOW']),'include_demo':bool_arg('include_demo')}

def common_rows(do_refresh=True):
    source=request.args.get('source','usgs'); feed=request.args.get('feed', current_app.config['DEFAULT_FEED_WINDOW'])
    refresh=refresh_if_needed(feed,bool_arg('refresh'),source) if do_refresh else 'cache'
    limit=safe_int(request.args.get('limit'),500,1,current_app.config['MAX_API_LIMIT']); sort=request.args.get('sort','time_desc')
    filt=filters_from_args(); rows=query_earthquakes(current_app.config['SQLITE_DB_PATH'],filt,limit,sort)
    return source, feed, refresh, filt, rows

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
    source,feed,refresh,filt,rows=common_rows(True); meta=all_meta(current_app.config['SQLITE_DB_PATH'])
    warnings=[]; demo_count=sum(1 for r in rows if r.get('is_bootstrap'))
    if demo_count: warnings.append('Demo data — not real earthquake locations.')
    if 'fallback' in refresh: warnings.append('Using cached data because one or more live source refreshes failed.')
    real_count=len(rows)-demo_count; last_epoch=max([int(feed_meta_value(meta,'last_successful_refresh_epoch',feed,s,'0') or 0) for s in enabled_source_names()] or [0])
    available_feeds=sorted({f for s in SOURCE_REGISTRY.values() for f in s.supported_feeds})
    return jsonify({'meta':{'source':(source if request.args.get('source') else feed),'requested_source':source,'feed':feed,'refresh_result':refresh,'last_refresh_epoch':last_epoch,'count':len(rows),'real_count':real_count,'demo_count':demo_count,'crosses_antimeridian':filt['crosses_antimeridian'],'available_sources':enabled_source_names(),'available_feeds':available_feeds,'warnings':warnings},'filters':filt,'count':len(rows),'source':source,'warnings':warnings,'data':rows})
@bp.route('/api/sources')
def api_sources():
    meta=all_meta(current_app.config['SQLITE_DB_PATH']); enabled=set(enabled_source_names()); out=[]
    for name,src in SOURCE_REGISTRY.items():
        if name=='usgs': continue
        last=max([int(feed_meta_value(meta,'last_successful_refresh_epoch',f,name,'0') or 0) for f in src.supported_feeds] or [0])
        out.append({'name':name,'display_name':src.display_name,'enabled':name in enabled,'coverage':src.coverage,'last_refresh':last,'last_error':feed_meta_value(meta,'last_refresh_error',src.supported_feeds[0] if src.supported_feeds else 'day',name,None),'record_count':feed_meta_value(meta,'last_record_count',src.supported_feeds[0] if src.supported_feeds else 'day',name,'0'),'attribution':src.attribution,'homepage_url':src.homepage_url,'supported_feeds':src.supported_feeds})
    return jsonify({'sources':out})
@bp.route('/api/refresh', methods=['POST'])
def api_refresh():
    token=current_app.config.get('ADMIN_TOKEN')
    if token and request.headers.get('X-Admin-Token') != token: return jsonify({'error':'unauthorized'}), 403
    payload=request.get_json(silent=True) or {}; return jsonify({'refresh_result':refresh_if_needed(payload.get('feed','day'), True, payload.get('source','all'))})
@bp.route('/api/summary')
def api_summary():
    source,feed,refresh,filt,rows=common_rows(True); return jsonify({'summary':analytics.summarize(rows),'count':len(rows),'source':source,'meta':{'source':source,'feed':feed,'refresh_result':refresh}})
@bp.route('/api/regions')
def api_regions(): source,feed,refresh,filt,rows=common_rows(True); return jsonify({'regions':analytics.regions(rows),'meta':{'source':source,'feed':feed}})
@bp.route('/api/timeseries')
def api_timeseries(): source,feed,refresh,filt,rows=common_rows(True); return jsonify({'interval':request.args.get('interval','hour'),'series':analytics.timeseries(rows, request.args.get('interval','hour')),'meta':{'source':source,'feed':feed}})
@bp.route('/api/forecast')
def api_forecast():
    source,feed,refresh,filt,rows=common_rows(True)
    lat=safe_float(request.args.get('lat'),37.7749); lon=safe_float(request.args.get('lon'),-122.4194); radius=safe_float(request.args.get('radius_km'),300); hours=safe_int(request.args.get('hours'),72,1,24*30); minmag=safe_float(request.args.get('min_magnitude'),2.5)
    result=model.predict(rows,current_app.config['MODEL_PATH'],lat,lon,radius,hours,minmag); result['meta']={'source':source,'feed':feed,'refresh_result':refresh}; return jsonify(result)
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
