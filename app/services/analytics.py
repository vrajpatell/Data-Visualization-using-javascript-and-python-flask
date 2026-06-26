from __future__ import annotations
from collections import Counter, defaultdict
import statistics
from datetime import datetime, timezone

def mag_bucket(m):
    if m is None: return 'unknown'
    if m<2: return '0-1.9'
    if m<3: return '2-2.9'
    if m<4: return '3-3.9'
    if m<5: return '4-4.9'
    return '5+'
def depth_bucket(d):
    if d is None: return 'unknown'
    if d<10: return '0-10 km'
    if d<35: return '10-35 km'
    if d<70: return '35-70 km'
    if d<150: return '70-150 km'
    return '150+ km'
def summarize(rows):
    mags=[r['magnitude'] for r in rows if r.get('magnitude') is not None]; depths=[r['depth'] for r in rows if r.get('depth') is not None]
    newest=max(rows, key=lambda r:r.get('time_ms') or 0) if rows else None
    return {'total_events':len(rows),'max_magnitude':max(mags) if mags else None,'average_magnitude':round(sum(mags)/len(mags),3) if mags else None,'median_magnitude':statistics.median(mags) if mags else None,'deepest_event':max(rows,key=lambda r:r.get('depth') or -999) if rows else None,'shallowest_event':min(rows,key=lambda r:r.get('depth') or 999999) if rows else None,'newest_event':newest,'high_risk_count':sum(1 for r in rows if (r.get('magnitude') or 0)>=4.5),'tsunami_count':sum(1 for r in rows if r.get('tsunami')),'significant_event_count':sum(1 for r in rows if (r.get('significance') or 0)>=600 or (r.get('magnitude') or 0)>=5),'top_regions':Counter(r.get('region') or 'Unknown' for r in rows).most_common(10),'magnitude_distribution':Counter(mag_bucket(r.get('magnitude')) for r in rows),'depth_distribution':Counter(depth_bucket(r.get('depth')) for r in rows),'hourly_trend':timeseries(rows,'hour'),'daily_trend':timeseries(rows,'day')}
def timeseries(rows, interval='hour'):
    b=defaultdict(lambda:{'count':0,'avg_magnitude':0,'max_magnitude':None}); sums=defaultdict(float)
    for r in rows:
        ms=r.get('time_ms') or 0; dt=datetime.fromtimestamp(ms/1000,tz=timezone.utc)
        key=dt.strftime('%Y-%m-%dT%H:00Z') if interval=='hour' else dt.strftime('%Y-%m-%d')
        m=r.get('magnitude') or 0; b[key]['count']+=1; sums[key]+=m; b[key]['max_magnitude']=m if b[key]['max_magnitude'] is None else max(b[key]['max_magnitude'],m)
    return [{'period':k,'count':v['count'],'avg_magnitude':round(sums[k]/v['count'],3),'max_magnitude':v['max_magnitude']} for k,v in sorted(b.items())]
def regions(rows):
    out=[]
    for reg,c in Counter(r.get('region') or 'Unknown' for r in rows).most_common():
        rr=[r for r in rows if (r.get('region') or 'Unknown')==reg]; mags=[r.get('magnitude') or 0 for r in rr]
        out.append({'region':reg,'count':c,'max_magnitude':max(mags) if mags else None,'avg_magnitude':round(sum(mags)/len(mags),2) if mags else None})
    return out
