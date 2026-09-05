from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
import httpx
from .db import Base, engine, SessionLocal, AuditLog, Channel, Movie, Series, Season, Episode
from .api import admin
from .xtream import XtreamClient, XtreamConfig
from .m3u import parse_m3u
from .features import public_url

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    source_type: Mapped[str] = mapped_column(String(30))
    host: Mapped[str] = mapped_column(String(500), default='')
    username: Mapped[str] = mapped_column(String(200), default='')
    secret: Mapped[str] = mapped_column(Text, default='')
    source_url: Mapped[str] = mapped_column(String(1000), default='')
    https: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)
router = APIRouter(prefix='/api/admin/sources', tags=['sources'])

class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(pattern='^(xtream|m3u)$')
    host: str = ''
    username: str = ''
    password: str = ''
    source_url: str = ''
    https: bool = True
    enabled: bool = True


def db_dep():
    db = SessionLocal()
    try: yield db
    finally: db.close()


def public_source(x):
    return {'id': x.id, 'name': x.name, 'source_type': x.source_type, 'host': x.host,
            'username': x.username, 'source_url': x.source_url, 'https': x.https,
            'enabled': x.enabled, 'last_sync': x.last_sync}

@router.get('')
def list_sources(db=Depends(db_dep), u=Depends(admin)):
    return [public_source(x) for x in db.query(Source).order_by(Source.name).all()]

@router.post('')
def create_source(data: SourceIn, db=Depends(db_dep), u=Depends(admin)):
    if data.source_type == 'xtream' and (not data.host or not data.username or not data.password): raise HTTPException(400, 'Xtream sources require host, username and password')
    if data.source_type == 'm3u' and not data.source_url: raise HTTPException(400, 'M3U sources require a playlist URL')
    if db.query(Source).filter_by(name=data.name.strip()).first(): raise HTTPException(409, 'A source with this name already exists')
    x = Source(name=data.name.strip(), source_type=data.source_type, host=data.host.strip(), username=data.username.strip(), secret=data.password, source_url=data.source_url.strip(), https=data.https, enabled=data.enabled)
    db.add(x); db.add(AuditLog(actor=u.username, action='create_source', target=x.name)); db.commit()
    return public_source(x)

@router.patch('/{source_id}')
def update_source(source_id: int, data: SourceIn, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    if data.source_type == 'xtream' and (not data.host or not data.username): raise HTTPException(400, 'Xtream source requires host and username')
    x.name = data.name.strip(); x.source_type = data.source_type; x.host = data.host.strip(); x.username = data.username.strip(); x.source_url = data.source_url.strip(); x.https = data.https; x.enabled = data.enabled
    if data.password: x.secret = data.password
    db.add(AuditLog(actor=u.username, action='update_source', target=x.name)); db.commit()
    return public_source(x)

@router.delete('/{source_id}')
def delete_source(source_id: int, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    name=x.name; db.delete(x); db.add(AuditLog(actor=u.username, action='delete_source', target=name)); db.commit(); return {'ok': True}

@router.post('/{source_id}/test')
def test_source(source_id: int, db=Depends(db_dep), u=Depends(admin)):
    x=db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    if x.source_type != 'xtream': return {'ok': True, 'message': 'M3U source is configured; playlist validation occurs during sync.'}
    try:
        info=XtreamClient(XtreamConfig(host=x.host,username=x.username,password=x.secret,https=x.https)).server_info()
        user_info=info.get('user_info') if isinstance(info,dict) else {}
        return {'ok': True, 'server': info.get('server_info',{}) if isinstance(info,dict) else {}, 'user': {'status': user_info.get('status'), 'exp_date': user_info.get('exp_date'), 'max_connections': user_info.get('max_connections'), 'active_cons': user_info.get('active_cons')}}
    except Exception as exc: raise HTTPException(400, f'Connection failed: {exc}')

@router.post('/{source_id}/toggle')
def toggle_source(source_id:int,db=Depends(db_dep),u=Depends(admin)):
    x=db.get(Source,source_id)
    if not x: raise HTTPException(404,'Source not found')
    x.enabled=not x.enabled; db.add(AuditLog(actor=u.username,action='toggle_source',target=x.name)); db.commit(); return public_source(x)


def sync_m3u(source, db):
    if not public_url(source.source_url): raise HTTPException(400, 'M3U URL must be a public HTTP(S) URL')
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as client: response=client.get(source.source_url); response.raise_for_status()
    except Exception as exc: raise HTTPException(400,f'Playlist fetch failed: {exc}')
    items=parse_m3u(response.text)
    if not items: raise HTTPException(400,'Playlist contains no channels')
    for item in items:
        channel=db.query(Channel).filter_by(name=item.name).first() or Channel(name=item.name)
        channel.group_name=item.group; channel.logo_url=item.logo; channel.stream_url=item.url; channel.epg_id=item.tvg_id; channel.active=True
        channel.number=int(item.channel_number) if item.channel_number.isdigit() else None
        channel.metadata_json=json.dumps({'source':'m3u','name':item.name,'url':item.url,'tvg_id':item.tvg_id,'tvg_name':item.tvg_name,'tvg_logo':item.logo,'group_title':item.group,'language':item.language,'country':item.country,'channel_number':item.channel_number,'radio':item.radio,'catchup':item.catchup,'catchup_source':item.catchup_source,'catchup_days':item.catchup_days,'attributes':item.attrs},ensure_ascii=False)
        db.add(channel)
    return {'channels':len(items),'movies':0,'series':0,'seasons':0,'episodes':0}


def sync_xtream(source, db):
    client=XtreamClient(XtreamConfig(host=source.host,username=source.username,password=source.secret,https=source.https))
    counts={'channels':0,'movies':0,'series':0,'seasons':0,'episodes':0}
    try:
        for item in client.live_streams():
            url=client.live_url(item.get('stream_id')); channel=db.query(Channel).filter_by(stream_url=url).first() or Channel(name=str(item.get('name') or 'Untitled channel'))
            channel.name=str(item.get('name') or channel.name); channel.group_name=str(item.get('category_name') or item.get('category_id') or 'Live TV'); channel.logo_url=str(item.get('stream_icon') or ''); channel.stream_url=url; channel.epg_id=str(item.get('epg_channel_id') or ''); channel.number=item.get('num'); channel.active=True
            channel.metadata_json=json.dumps(item,ensure_ascii=False,default=str); db.add(channel); counts['channels']+=1
        for item in client.vod_streams():
            stream_id=item.get('stream_id'); url=client.movie_url(stream_id); movie=db.query(Movie).filter_by(stream_url=url).first() or Movie(title=str(item.get('name') or 'Untitled movie'))
            movie.title=str(item.get('name') or movie.title); movie.poster_url=str(item.get('stream_icon') or ''); movie.stream_url=url; movie.active=True; movie.year=item.get('year'); movie.genre=str(item.get('genre') or ''); movie.synopsis=str(item.get('plot') or item.get('description') or '')
            movie.duration=item.get('duration_secs') or item.get('duration'); movie.backdrop_url=str(item.get('backdrop_path') or ''); movie.metadata_json=json.dumps(item,ensure_ascii=False,default=str); db.add(movie); counts['movies']+=1
        for item in client.series():
            ext_id=item.get('series_id'); title=str(item.get('name') or 'Untitled series'); series=db.query(Series).filter_by(title=title).first() or Series(title=title)
            series.poster_url=str(item.get('cover') or ''); series.backdrop_url=str(item.get('backdrop_path') or ''); series.synopsis=str(item.get('plot') or item.get('description') or ''); series.year=item.get('releaseDate') or item.get('year'); series.genre=str(item.get('genre') or ''); series.active=True; series.metadata_json=json.dumps(item,ensure_ascii=False,default=str); db.add(series); db.flush(); counts['series']+=1
            info=client.series_info(int(ext_id))
            for season_number, episodes in (info.get('episodes') or {}).items():
                sn=int(season_number); season=db.query(Season).filter_by(series_id=series.id,season_number=sn).first() or Season(series_id=series.id,season_number=sn,title=f'Season {sn}')
                season.metadata_json=json.dumps(info.get('seasons',{}).get(str(sn), info.get('seasons',{}).get(sn,{})),ensure_ascii=False,default=str); db.add(season); db.flush(); counts['seasons']+=1
                for ep in episodes or []:
                    stream_id=ep.get('id') or ep.get('stream_id'); url=client.series_episode_url(stream_id); num=int(ep.get('episode_num') or 0); episode=db.query(Episode).filter_by(season_id=season.id,episode_number=num).first() or Episode(season_id=season.id,episode_number=num,title=str(ep.get('title') or 'Episode'))
                    episode.title=str(ep.get('title') or episode.title); episode.synopsis=str(ep.get('plot') or ep.get('description') or ''); episode.stream_url=url; episode.duration=ep.get('duration_secs') or ep.get('duration'); episode.metadata_json=json.dumps(ep,ensure_ascii=False,default=str); db.add(episode); counts['episodes']+=1
    except Exception as exc: raise HTTPException(400,f'Xtream sync failed: {exc}')
    return counts

@router.post('/{source_id}/sync')
def sync_source(source_id:int,db=Depends(db_dep),u=Depends(admin)):
    source=db.get(Source,source_id)
    if not source: raise HTTPException(404,'Source not found')
    if not source.enabled: raise HTTPException(409,'Source is disabled')
    counts=sync_m3u(source,db) if source.source_type=='m3u' else sync_xtream(source,db); source.last_sync=datetime.utcnow(); db.add(source); db.add(AuditLog(actor=u.username,action='sync_source',target=source.name)); db.commit(); return {'ok':True,'source':source.name,'synced_at':source.last_sync,**counts}
