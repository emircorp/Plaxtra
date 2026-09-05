from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, engine, SessionLocal, AuditLog
from .api import admin
from .xtream import XtreamClient, XtreamConfig

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
    try:
        yield db
    finally:
        db.close()


def public_source(x):
    return {'id': x.id, 'name': x.name, 'source_type': x.source_type, 'host': x.host,
            'username': x.username, 'source_url': x.source_url, 'https': x.https,
            'enabled': x.enabled, 'last_sync': x.last_sync}

@router.get('')
def list_sources(db=Depends(db_dep), u=Depends(admin)):
    return [public_source(x) for x in db.query(Source).order_by(Source.name).all()]

@router.post('')
def create_source(data: SourceIn, db=Depends(db_dep), u=Depends(admin)):
    if data.source_type == 'xtream' and (not data.host or not data.username or not data.password):
        raise HTTPException(400, 'Xtream sources require host, username and password')
    if data.source_type == 'm3u' and not data.source_url:
        raise HTTPException(400, 'M3U sources require a playlist URL')
    if db.query(Source).filter_by(name=data.name.strip()).first():
        raise HTTPException(409, 'A source with this name already exists')
    x = Source(name=data.name.strip(), source_type=data.source_type, host=data.host.strip(),
               username=data.username.strip(), secret=data.password, source_url=data.source_url.strip(),
               https=data.https, enabled=data.enabled)
    db.add(x); db.add(AuditLog(actor=u.username, action='create_source', target=x.name)); db.commit()
    return public_source(x)

@router.patch('/{source_id}')
def update_source(source_id: int, data: SourceIn, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    if data.source_type == 'xtream' and (not data.host or not data.username):
        raise HTTPException(400, 'Xtream source requires host and username')
    x.name = data.name.strip(); x.source_type = data.source_type; x.host = data.host.strip()
    x.username = data.username.strip(); x.source_url = data.source_url.strip(); x.https = data.https; x.enabled = data.enabled
    if data.password: x.secret = data.password
    db.add(AuditLog(actor=u.username, action='update_source', target=x.name)); db.commit()
    return public_source(x)

@router.delete('/{source_id}')
def delete_source(source_id: int, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    name = x.name; db.delete(x); db.add(AuditLog(actor=u.username, action='delete_source', target=name)); db.commit()
    return {'ok': True}

@router.post('/{source_id}/test')
def test_source(source_id: int, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    if x.source_type != 'xtream':
        return {'ok': True, 'message': 'M3U source is configured; playlist validation occurs during sync.'}
    try:
        info = XtreamClient(XtreamConfig(host=x.host, username=x.username, password=x.secret, https=x.https)).server_info()
        return {'ok': True, 'server_info': info}
    except Exception as exc:
        raise HTTPException(400, f'Connection failed: {exc}')

@router.post('/{source_id}/toggle')
def toggle_source(source_id: int, db=Depends(db_dep), u=Depends(admin)):
    x = db.get(Source, source_id)
    if not x: raise HTTPException(404, 'Source not found')
    x.enabled = not x.enabled; db.add(AuditLog(actor=u.username, action='toggle_source', target=x.name)); db.commit()
    return public_source(x)
