from __future__ import annotations
import json, random, sqlite3, time
from pathlib import Path
from typing import Any
from app.utils import rough_region

COLUMNS=['id','source','time_ms','updated_ms','place','magnitude','longitude','latitude','depth','alert','tsunami','significance','felt','cdi','mmi','status','event_type','network','code','url','detail_url','mag_type','gap','dmin','rms','nst','region']

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(db_path, timeout=30)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL'); conn.execute('PRAGMA busy_timeout=5000')
    return conn

def init_db(db_path: str) -> None:
    with connect(db_path) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS earthquakes (
            id TEXT PRIMARY KEY, source TEXT DEFAULT 'usgs', time_ms INTEGER, updated_ms INTEGER, place TEXT, magnitude REAL,
            longitude REAL, latitude REAL, depth REAL, alert TEXT, tsunami INTEGER, significance INTEGER,
            felt INTEGER, cdi REAL, mmi REAL, status TEXT, event_type TEXT, network TEXT, code TEXT,
            url TEXT, detail_url TEXT, mag_type TEXT, gap REAL, dmin REAL, rms REAL, nst INTEGER,
            region TEXT, ingested_at INTEGER, source_feed TEXT, is_bootstrap INTEGER DEFAULT 0)''')

        existing={r['name'] for r in c.execute('PRAGMA table_info(earthquakes)').fetchall()}
        if 'source' not in existing: c.execute("ALTER TABLE earthquakes ADD COLUMN source TEXT DEFAULT 'usgs'")
        if 'raw_source' not in existing: c.execute("ALTER TABLE earthquakes ADD COLUMN raw_source TEXT")
        c.execute('''CREATE TABLE IF NOT EXISTS refresh_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)''')
        for idx,col in [('idx_quakes_time','time_ms'),('idx_quakes_mag','magnitude'),('idx_quakes_lat','latitude'),('idx_quakes_lon','longitude'),('idx_quakes_region','region'),('idx_quakes_source','source'),('idx_quakes_feed','source_feed'),('idx_quakes_bootstrap','is_bootstrap')]:
            c.execute(f'CREATE INDEX IF NOT EXISTS {idx} ON earthquakes({col})')
        c.commit()

def feed_meta_key(k: str, feed: str, source: str='usgs') -> str:
    return f'{k}:{source}:{feed}'

def set_meta(c, k, v): c.execute('INSERT INTO refresh_metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v)))
def get_meta(db_path: str, k: str, default: str='') -> str:
    with connect(db_path) as c:
        r=c.execute('SELECT value FROM refresh_metadata WHERE key=?',(k,)).fetchone(); return r['value'] if r else default

def all_meta(db_path: str) -> dict[str,str]:
    with connect(db_path) as c: return {r['key']:r['value'] for r in c.execute('SELECT key,value FROM refresh_metadata')}

def upsert_earthquakes(db_path: str, rows: list[dict[str,Any]], source_feed='unknown', is_bootstrap=False) -> int:
    now=int(time.time())
    vals=[]
    for r in rows:
        r=dict(r); r.setdefault('source', 'bootstrap_demo' if is_bootstrap else ('usgs' if str(source_feed) in {'hour','day','7day','30day','significant','m1','m2.5','m4.5'} else str(r.get('source') or 'usgs'))); r.setdefault('region', rough_region(r.get('latitude'), r.get('longitude'), r.get('place','')))
        vals.append(tuple(r.get(col) for col in COLUMNS)+(now,source_feed,1 if is_bootstrap else 0))
    ph=','.join(['?']*(len(COLUMNS)+3))
    updates=','.join([f'{c}=excluded.{c}' for c in COLUMNS[1:]]+['ingested_at=excluded.ingested_at','source_feed=excluded.source_feed','is_bootstrap=excluded.is_bootstrap'])
    with connect(db_path) as c:
        c.executemany(f'INSERT INTO earthquakes({",".join(COLUMNS)},ingested_at,source_feed,is_bootstrap) VALUES({ph}) ON CONFLICT(id) DO UPDATE SET {updates}', vals)
        source_name = ('bootstrap_demo' if is_bootstrap else ((rows[0].get('source') if rows else None) or ('usgs' if str(source_feed) in {'hour','day','7day','30day','significant','m1','m2.5','m4.5'} else 'usgs')))
        set_meta(c,'last_successful_refresh_epoch',now); set_meta(c,'last_refresh_source',source_name); set_meta(c,'last_record_count',len(rows))
        set_meta(c,feed_meta_key('last_successful_refresh_epoch',source_feed,source_name),now); set_meta(c,feed_meta_key('last_refresh_source',source_feed,source_name),source_name); set_meta(c,feed_meta_key('last_record_count',source_feed,source_name),len(rows)); set_meta(c,feed_meta_key('last_refresh_error',source_feed,source_name),'')
        # legacy feed-only metadata for backward compatibility
        set_meta(c,f'last_successful_refresh_epoch:{source_feed}',now); set_meta(c,f'last_refresh_source:{source_feed}',source_feed); set_meta(c,f'last_record_count:{source_feed}',len(rows)); set_meta(c,f'last_refresh_error:{source_feed}','')
        c.commit()
    return len(rows)

def seed_bootstrap_if_empty(db_path: str, enabled=True) -> None:
    if not enabled: return
    with connect(db_path) as c:
        if c.execute('SELECT COUNT(*) n FROM earthquakes').fetchone()['n']>0: return
    rng=random.Random(7); now_ms=int(time.time()*1000)
    places=['Bootstrap demo, California','Bootstrap demo, Alaska','Bootstrap demo, Japan','Bootstrap demo, Chile','Bootstrap demo, Indonesia']
    rows=[]
    for i in range(180):
        lat=rng.uniform(-55,65); lon=rng.uniform(-170,170); mag=round(rng.uniform(1,6.4),1)
        rows.append({'id':f'bootstrap-{i}','source':'bootstrap_demo','time_ms':now_ms-i*3600_000,'updated_ms':now_ms,'place':rng.choice(places),'magnitude':mag,'longitude':round(lon,3),'latitude':round(lat,3),'depth':round(rng.uniform(2,140),1),'tsunami':0,'significance':int(mag*100),'event_type':'earthquake','region':rough_region(lat,lon,rng.choice(places))})
    upsert_earthquakes(db_path, rows, 'bootstrap_demo', True)

def query_earthquakes(db_path: str, filters: dict[str,Any], limit: int, sort='time_desc') -> list[dict[str,Any]]:
    where=[]; args=[]
    for key,col,op in [('mag_min','magnitude','>='),('mag_max','magnitude','<='),('lat_min','latitude','>='),('lat_max','latitude','<=')]:
        if filters.get(key) is not None: where.append(f'{col} {op} ?'); args.append(filters[key])
    if filters.get('lon1') is not None and filters.get('lon2') is not None:
        lon1=float(filters['lon1']); lon2=float(filters['lon2'])
        if lon1 <= lon2: where.append('longitude BETWEEN ? AND ?'); args.extend([lon1,lon2])
        else: where.append('(longitude >= ? OR longitude <= ?)'); args.extend([lon1,lon2])
    else:
        for key,col,op in [('lon_min','longitude','>='),('lon_max','longitude','<=')]:
            if filters.get(key) is not None: where.append(f'{col} {op} ?'); args.append(filters[key])
    if filters.get('start_time') is not None: where.append('time_ms >= ?'); args.append(filters['start_time'])
    if filters.get('end_time') is not None: where.append('time_ms <= ?'); args.append(filters['end_time'])
    if filters.get('source') and filters.get('source')!='all':
        src=filters['source']; src='usgs' if src in {'usgs','usgs_geojson'} else src
        where.append('source = ?'); args.append(src)
    if filters.get('source_feed') and filters.get('source_feed')!='all': where.append('source_feed = ?'); args.append(filters['source_feed'])
    if filters.get('include_demo') is False: where.append('COALESCE(is_bootstrap,0)=0')
    sql='SELECT * FROM earthquakes '+(('WHERE '+ ' AND '.join(where)) if where else '')
    order={'time_asc':'time_ms ASC','magnitude_desc':'magnitude DESC','magnitude_asc':'magnitude ASC'}.get(sort,'time_ms DESC')
    sql += f' ORDER BY {order} LIMIT ?'; args.append(limit)
    with connect(db_path) as c: return [dict(r) for r in c.execute(sql,args).fetchall()]

def count_records(db_path: str) -> int:
    with connect(db_path) as c: return c.execute('SELECT COUNT(*) n FROM earthquakes').fetchone()['n']

def all_records(db_path: str, limit=10000) -> list[dict[str,Any]]: return query_earthquakes(db_path, {}, limit, 'time_asc')
