from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .api import admin
from .db import SessionLocal, Movie, Series, Season, Episode, Channel, AuditLog
from .xtream import XtreamClient, XtreamConfig

router = APIRouter(prefix='/api/admin/xtream', tags=['xtream'])

class XtreamConnection(BaseModel):
    host: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    https: bool = True

class XtreamImportOptions(XtreamConnection):
    import_live: bool = True
    import_vod: bool = True
    import_series: bool = True


def db_dep():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def client(data: XtreamConnection):
    return XtreamClient(XtreamConfig(**data.model_dump()))


def text(value, default=''):
    return str(value or default).strip()


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_seconds(value):
    if value is None:
        return None
    try:
        if isinstance(value, str) and ':' in value:
            parts = [int(x) for x in value.split(':')]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return int(float(value))
    except (TypeError, ValueError):
        return None


def category_map(items):
    return {text(x.get('category_id')): text(x.get('category_name'), 'General') for x in (items or []) if x.get('category_id') is not None}


@router.post('/test')
def test_connection(data: XtreamConnection, u=Depends(admin)):
    try:
        info = client(data).server_info()
        return {'ok': True, 'server_info': info}
    except Exception as exc:
        raise HTTPException(400, f'Xtream connection failed: {exc}')


@router.post('/preview')
def preview(data: XtreamConnection, u=Depends(admin)):
    try:
        c = client(data)
        return {
            'ok': True,
            'live_categories': c.live_categories(),
            'vod_categories': c.vod_categories(),
            'series_categories': c.series_categories(),
        }
    except Exception as exc:
        raise HTTPException(400, f'Xtream connection failed: {exc}')


@router.post('/import')
def import_source(data: XtreamImportOptions, db: Session = Depends(db_dep), u=Depends(admin)):
    c = client(data)
    counts = {'live': 0, 'movies': 0, 'series': 0, 'seasons': 0, 'episodes': 0}
    try:
        live_categories = category_map(c.live_categories()) if data.import_live else {}
        vod_categories = category_map(c.vod_categories()) if data.import_vod else {}
        series_categories = category_map(c.series_categories()) if data.import_series else {}

        if data.import_live:
            for item in c.live_streams():
                stream_id = item.get('stream_id')
                if stream_id is None:
                    continue
                url = c.live_url(stream_id, text(item.get('stream_type'), 'm3u8'))
                name = text(item.get('name'), f'Channel {stream_id}')
                existing = db.query(Channel).filter_by(name=name, stream_url=url).first()
                if existing:
                    existing.group_name = live_categories.get(text(item.get('category_id')), existing.group_name)
                    existing.logo_url = text(item.get('stream_icon'), existing.logo_url)
                    existing.epg_id = text(item.get('epg_channel_id'), existing.epg_id)
                    existing.number = as_int(item.get('num'))
                else:
                    db.add(Channel(name=name, group_name=live_categories.get(text(item.get('category_id')), 'General'), logo_url=text(item.get('stream_icon')), stream_url=url, epg_id=text(item.get('epg_channel_id')), number=as_int(item.get('num'))))
                counts['live'] += 1

        if data.import_vod:
            for item in c.vod_streams():
                stream_id = item.get('stream_id')
                if stream_id is None:
                    continue
                ext = text(item.get('container_extension'), 'mp4')
                url = c.movie_url(stream_id, ext)
                name = text(item.get('name'), f'Movie {stream_id}')
                existing = db.query(Movie).filter_by(title=name, stream_url=url).first()
                values = dict(synopsis=text(item.get('plot')), year=as_int(item.get('year')), genre=vod_categories.get(text(item.get('category_id')), ''), poster_url=text(item.get('stream_icon')), backdrop_url=text(item.get('backdrop_path')), stream_url=url, duration=as_seconds(item.get('duration_secs')))
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                else:
                    db.add(Movie(title=name, **values))
                counts['movies'] += 1

        if data.import_series:
            for item in c.series():
                series_id = item.get('series_id')
                if series_id is None:
                    continue
                name = text(item.get('name'), f'Series {series_id}')
                existing = db.query(Series).filter_by(title=name).first()
                if not existing:
                    existing = Series(title=name)
                    db.add(existing)
                    db.flush()
                existing.year = as_int(item.get('year'))
                existing.genre = series_categories.get(text(item.get('category_id')), text(item.get('genre')))
                existing.poster_url = text(item.get('cover'))
                existing.backdrop_url = text(item.get('backdrop_path'))
                info = c.series_info(int(series_id)) or {}
                info_meta = info.get('info') or {}
                existing.synopsis = text(info_meta.get('plot'), existing.synopsis)
                seasons = info.get('episodes') or {}
                if isinstance(seasons, list):
                    seasons = {'1': seasons}
                for season_key, episode_items in seasons.items():
                    season_number = as_int(season_key) or 1
                    season = db.query(Season).filter_by(series_id=existing.id, season_number=season_number).first()
                    if not season:
                        season = Season(series_id=existing.id, season_number=season_number, title=f'Season {season_number}')
                        db.add(season)
                        db.flush()
                        counts['seasons'] += 1
                    for ep in episode_items or []:
                        episode_number = as_int(ep.get('episode_num')) or 1
                        stream_id = ep.get('id') or ep.get('stream_id')
                        if stream_id is None:
                            continue
                        ext = text(ep.get('container_extension'), 'mp4')
                        url = c.series_episode_url(stream_id, ext)
                        episode = db.query(Episode).filter_by(season_id=season.id, episode_number=episode_number).first()
                        values = dict(title=text(ep.get('title'), f'Episode {episode_number}'), synopsis=text(ep.get('plot')), stream_url=url, duration=as_seconds(ep.get('duration_secs')))
                        if episode:
                            for key, value in values.items():
                                setattr(episode, key, value)
                        else:
                            db.add(Episode(season_id=season.id, episode_number=episode_number, **values))
                        counts['episodes'] += 1
                counts['series'] += 1

        db.add(AuditLog(actor=u.username, action='xtream_import', target=data.host))
        db.commit()
        return {'ok': True, 'counts': counts, 'synced_at': datetime.utcnow().isoformat() + 'Z'}
    except Exception as exc:
        db.rollback()
        raise HTTPException(400, f'Xtream import failed: {exc}')
