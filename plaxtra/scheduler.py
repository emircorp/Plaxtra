import asyncio
import os
from .db import SessionLocal
from .sources import Source, sync_m3u, sync_xtream

async def sync_enabled_sources_once():
    db = SessionLocal()
    try:
        for source in db.query(Source).filter_by(enabled=True).all():
            try:
                if source.source_type == 'm3u':
                    sync_m3u(source, db)
                elif source.source_type == 'xtream':
                    sync_xtream(source, db)
                source.last_sync = __import__('datetime').datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()

async def scheduler_loop():
    interval = max(3600, int(os.getenv('PLAXTRA_SYNC_INTERVAL', '21600')))
    while True:
        await sync_enabled_sources_once()
        await asyncio.sleep(interval)
