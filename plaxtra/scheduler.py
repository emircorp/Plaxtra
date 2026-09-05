import asyncio
import logging
import os
from datetime import datetime
from .db import SessionLocal, AuditLog
from .sources import Source, sync_m3u, sync_xtream

log = logging.getLogger('plaxtra.scheduler')

def sync_enabled_sources_sync():
    db = SessionLocal()
    try:
        for source in db.query(Source).filter_by(enabled=True).all():
            try:
                if source.source_type == 'm3u':
                    counts = sync_m3u(source, db)
                elif source.source_type == 'xtream':
                    counts = sync_xtream(source, db)
                else:
                    continue
                source.last_sync = datetime.utcnow()
                db.add(AuditLog(actor='system', action='scheduled_sync', target=source.name))
                db.commit()
                log.info('Scheduled sync complete: %s (%s)', source.name, counts)
            except Exception:
                db.rollback()
                log.exception('Scheduled sync failed for source %s', source.name)
    finally:
        db.close()

async def sync_enabled_sources_once():
    await asyncio.to_thread(sync_enabled_sources_sync)

async def scheduler_loop():
    interval = max(3600, int(os.getenv('PLAXTRA_SYNC_INTERVAL', '21600')))
    while True:
        await sync_enabled_sources_once()
        await asyncio.sleep(interval)
