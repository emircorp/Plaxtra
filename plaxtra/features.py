from datetime import datetime
from ipaddress import ip_address
from socket import getaddrinfo
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from .db import SessionLocal, Series, Season, Episode, Channel, Playlist, Setting, AuditLog
from .m3u import parse_m3u

router=APIRouter(prefix='/api',tags=['library'])
def db_dep():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def current_user(request:Request,db:Session=Depends(db_dep)):
    uid=request.session.get('user_id'); user=db.get(__import__('plaxtra.db',fromlist=['User']).User,uid) if uid else None
    if not user or not user.active: raise HTTPException(401,'Login required')
    return user

def admin(user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access required')
    return user

def public_url(url:str):
    p=urlparse(url)
    if p.scheme not in {'http','https'} or not p.hostname: return False
    try:
        for info in getaddrinfo(p.hostname,None):
            addr=ip_address(info[4][0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved: return False
    except OSError: return False
    return True

class SeriesIn(BaseModel): title:str; synopsis:str=''; year:int|None=None; genre:str=''; poster_url:str=''; backdrop_url:str=''
class SeasonIn(BaseModel): season_number:int; title:str=''
class EpisodeIn(BaseModel): episode_number:int; title:str; synopsis:str=''; stream_url:str=''; duration:int|None=None
class PlaylistIn(BaseModel): name:str; source_url:HttpUrl

@router.get('/series')
def list_series(db:Session=Depends(db_dep)):
    return [{'id':x.id,'title':x.title,'year':x.year,'genre':x.genre,'poster_url':x.poster_url,'backdrop_url':x.backdrop_url} for x in db.query(Series).filter_by(active=True).order_by(Series.title).all()]

@router.get('/series/{series_id}')
def series_detail(series_id:int,db:Session=Depends(db_dep)):
    s=db.get(Series,series_id)
    if not s: raise HTTPException(404,'Series not found')
    seasons=db.query(Season).filter_by(series_id=s.id).order_by(Season.season_number).all()
    return {'id':s.id,'title':s.title,'synopsis':s.synopsis,'year':s.year,'genre':s.genre,'poster_url':s.poster_url,'backdrop_url':s.backdrop_url,'seasons':[{'id':z.id,'season_number':z.season_number,'title':z.title,'episodes':[{'id':e.id,'episode_number':e.episode_number,'title':e.title,'synopsis':e.synopsis,'duration':e.duration,'stream_url':e.stream_url} for e in z.episodes]} for z in seasons]}

@router.post('/admin/series')
def create_series(data:SeriesIn,db:Session=Depends(db_dep),u=Depends(admin)):
    item=Series(**data.model_dump()); db.add(item); db.add(AuditLog(actor=u.username,action='create_series',target=data.title)); db.commit(); db.refresh(item); return {'id':item.id}

@router.post('/admin/series/{series_id}/seasons')
def create_season(series_id:int,data:SeasonIn,db:Session=Depends(db_dep),u=Depends(admin)):
    if not db.get(Series,series_id): raise HTTPException(404,'Series not found')
    item=Season(series_id=series_id,**data.model_dump()); db.add(item); db.commit(); db.refresh(item); return {'id':item.id}

@router.post('/admin/seasons/{season_id}/episodes')
def create_episode(season_id:int,data:EpisodeIn,db:Session=Depends(db_dep),u=Depends(admin)):
    if data.stream_url and not public_url(data.stream_url): raise HTTPException(400,'Stream URL must resolve to a public HTTP(S) address')
    if not db.get(Season,season_id): raise HTTPException(404,'Season not found')
    item=Episode(season_id=season_id,**data.model_dump()); db.add(item); db.commit(); db.refresh(item); return {'id':item.id}

@router.post('/admin/playlists/import')
def import_playlist(data:PlaylistIn,db:Session=Depends(db_dep),u=Depends(admin)):
    if not public_url(str(data.source_url)): raise HTTPException(400,'Playlist host must resolve to a public HTTP(S) address')
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client: response=client.get(str(data.source_url)); response.raise_for_status()
    except Exception as exc: raise HTTPException(400,f'Playlist fetch failed: {exc}')
    items=parse_m3u(response.text); playlist=Playlist(name=data.name,source_url=str(data.source_url),last_sync=datetime.utcnow()); db.add(playlist); db.flush(); imported=0
    for item in items:
        if public_url(item.url): db.add(Channel(name=item.name,group_name=item.group,logo_url=item.logo,stream_url=item.url,epg_id=item.tvg_id)); imported+=1
    db.add(AuditLog(actor=u.username,action='import_playlist',target=data.name)); db.commit(); return {'playlist_id':playlist.id,'imported':imported}

@router.get('/branding')
def branding(db:Session=Depends(db_dep)):
    return {x.key:x.value for x in db.query(Setting).filter(Setting.key.in_(['app_name','tagline','accent','attribution'])).all()}
