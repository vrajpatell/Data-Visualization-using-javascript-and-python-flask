from __future__ import annotations
import json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.utils import DISCLAIMER, haversine_km
FEATURE_NAMES=['event_count_24h','event_count_7d','max_mag_7d','avg_mag_7d','count_m25_7d','count_m45_7d','mean_depth_7d','time_since_last_hours','recent_acceleration','aftershock_large_nearby','lat','lon','hour','day_of_week']

def nearby(rows, lat, lon, radius):
    out=[]
    for r in rows:
        if r.get('latitude') is None or r.get('longitude') is None: continue
        d=haversine_km(lat,lon,float(r['latitude']),float(r['longitude']))
        if d<=radius:
            x=dict(r); x['distance_km']=round(d,1); out.append(x)
    return sorted(out,key=lambda r:r.get('time_ms') or 0, reverse=True)
def feature_vector(rows, lat, lon, radius, hours, min_mag):
    now=max([r.get('time_ms') or 0 for r in rows], default=int(datetime.now(timezone.utc).timestamp()*1000)); near=nearby(rows,lat,lon,radius)
    def win(h): return [r for r in near if now-(r.get('time_ms') or 0)<=h*3600_000]
    w24=win(24); w7=win(24*7); mags=[r.get('magnitude') or 0 for r in w7]; depths=[r.get('depth') or 0 for r in w7]
    last=max([r.get('time_ms') or 0 for r in near], default=0)
    f={'event_count_24h':len(w24),'event_count_7d':len(w7),'max_mag_7d':max(mags) if mags else 0,'avg_mag_7d':(sum(mags)/len(mags)) if mags else 0,'count_m25_7d':sum(1 for m in mags if m>=2.5),'count_m45_7d':sum(1 for m in mags if m>=4.5),'mean_depth_7d':(sum(depths)/len(depths)) if depths else 0,'time_since_last_hours':round((now-last)/3600_000,2) if last else 999,'recent_acceleration':len(w24)-((len(w7)-len(w24))/6 if len(w7)>len(w24) else 0),'aftershock_large_nearby':1 if any((r.get('magnitude') or 0)>=5 for r in w24) else 0,'lat':lat,'lon':lon,'hour':datetime.fromtimestamp(now/1000,tz=timezone.utc).hour,'day_of_week':datetime.fromtimestamp(now/1000,tz=timezone.utc).weekday()}
    return f, near[:10]
def heuristic(features):
    score=0
    score+=min(features['event_count_24h']*4,25)+min(features['event_count_7d']*1.4,25)+min(features['max_mag_7d']*7,28)+features['count_m45_7d']*8
    if features['aftershock_large_nearby']: score+=15
    if features['time_since_last_hours']<6: score+=10
    score=max(0,min(100,score)); return score
def bucket(score): return 'high' if score>=75 else 'elevated' if score>=50 else 'moderate' if score>=25 else 'low'
def load_artifact(path):
    p=Path(path)
    if p.exists():
        try:
            import joblib
            return joblib.load(p)
        except Exception: return None
    return None
def predict(rows, model_path, lat, lon, radius, hours, min_mag):
    feats, near=feature_vector(rows,lat,lon,radius,hours,min_mag); score=heuristic(feats); confidence='low'; source='heuristic_baseline'
    art=load_artifact(model_path)
    if art and art.get('model'):
        try:
            import pandas as pd
            proba=float(art['model'].predict_proba(pd.DataFrame([feats])[FEATURE_NAMES])[0][1]); score=round((score*0.45+proba*100*0.55),2); confidence='moderate'; source='supervised_model_plus_heuristic'
        except Exception: pass
    top=sorted(feats.items(), key=lambda kv: abs(float(kv[1])) if isinstance(kv[1],(int,float)) else 0, reverse=True)[:6]
    return {'risk_score':round(score,2),'estimated_probability':round(score/100,3),'probability_bucket':bucket(score),'expected_activity_count':round(feats['event_count_24h']*(hours/24)+0.2*feats['event_count_7d'],2),'model_confidence':confidence,'model_source':source,'top_contributing_features':[{'feature':k,'value':v} for k,v in top],'nearby_recent_events':near[:8],'explanation':'Risk score blends recent nearby activity, magnitude/depth patterns, aftershock heuristics, and an optional trained classifier when enough cached data exists.','warning':DISCLAIMER}
def train(rows, model_path):
    if len(rows)<80: return {'trained':False,'reason':'not_enough_rows','training_rows':len(rows)}
    try:
        import joblib, numpy as np, pandas as pd
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
    except Exception as exc:
        return {'trained':False,'reason':'ml_dependencies_unavailable','error':str(exc),'training_rows':len(rows)}
    df=pd.DataFrame(rows).sort_values('time_ms'); samples=[]; target=[]
    for _,r in df.iterrows():
        lat=float(r.latitude); lon=float(r.longitude); t=int(r.time_ms); hist=[x for x in rows if (x.get('time_ms') or 0) <= t]
        feats,_=feature_vector(hist,lat,lon,250,72,2.5); future=[x for x in rows if t < (x.get('time_ms') or 0) <= t+72*3600_000 and haversine_km(lat,lon,x.get('latitude'),x.get('longitude'))<=250 and (x.get('magnitude') or 0)>=2.5]
        samples.append(feats); target.append(1 if future else 0)
    if len(set(target))<2: return {'trained':False,'reason':'single_class_target','training_rows':len(target)}
    X=pd.DataFrame(samples)[FEATURE_NAMES]; y=np.array(target); split=int(len(X)*0.75); Xtr,Xte=X.iloc[:split],X.iloc[split:]; ytr,yte=y[:split],y[split:]
    model=HistGradientBoostingClassifier(max_iter=80, learning_rate=0.08).fit(Xtr,ytr); pred=model.predict(Xte); proba=model.predict_proba(Xte)[:,1]
    metrics={'accuracy':float(accuracy_score(yte,pred)),'precision':float(precision_score(yte,pred,zero_division=0)),'recall':float(recall_score(yte,pred,zero_division=0)),'f1':float(f1_score(yte,pred,zero_division=0)),'confusion_matrix':confusion_matrix(yte,pred).tolist()}
    if len(set(yte))>1: metrics['roc_auc']=float(roc_auc_score(yte,proba))
    meta={'model_version':'2026.06','trained_at':datetime.now(timezone.utc).isoformat(),'training_rows':len(X),'metrics':metrics,'feature_names':FEATURE_NAMES,'artifact_path':model_path}
    Path(model_path).parent.mkdir(parents=True,exist_ok=True); joblib.dump({'model':model,'metadata':meta}, model_path); Path(model_path+'.json').write_text(json.dumps(meta,indent=2))
    return {'trained':True, **meta}
def status(model_path):
    art=load_artifact(model_path); meta=(art or {}).get('metadata',{})
    return {'model_exists':bool(art),'model_version':meta.get('model_version'),'trained_at':meta.get('trained_at'),'training_rows':meta.get('training_rows',0),'metrics':meta.get('metrics',{}),'feature_names':meta.get('feature_names',FEATURE_NAMES),'artifact_path':model_path}
