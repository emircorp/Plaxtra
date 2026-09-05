# Plaxtra

Plaxtra is a self-hosted, rebrandable streaming platform for authorized media sources. It is an independent implementation with an original UI and codebase.

## Current capabilities

- Movies, series, seasons and episodes
- Live TV channels
- M3U/M3U8 source import
- Xtream Codes source integration
- HLS playback with HLS.js where needed
- User accounts and first-run administrator setup
- Continue Watching with per-user playback progress
- Favorites API
- Search across the media catalog
- Admin source manager with test, enable/disable, delete and manual sync
- Automatic background source synchronization
- SQLite persistence
- FastAPI API documentation at `/api/docs`
- Responsive web UI

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000`. On the first run, use `/setup` to create the administrator account.

## Configuration

Copy `.env.example` to `.env` and set a strong `PLAXTRA_SECRET_KEY` for deployments that are not purely local. `PLAXTRA_SYNC_INTERVAL` controls automatic source synchronization; the scheduler enforces a minimum interval of one hour.

Plaxtra is designed to run directly with Python and Uvicorn. Docker is not required.

## Sources

Configure authorized M3U or Xtream Codes sources from the Admin area. Automatic synchronization runs in the application process and uses an internal Python worker; Redis, Celery and other external job infrastructure are not required.

Plaxtra does not expose an arbitrary media proxy. Stream URLs are consumed directly by the browser/player.

## Security

Do not configure sources or media that you are not authorized to access. For production deployments, use HTTPS, a strong secret key and secure cookies. Remote M3U playlist imports reject non-public HTTP(S) destinations to reduce SSRF risk.

## License and attribution

Plaxtra uses the custom **PLAXTRA ATTRIBUTION LICENSE v1.0** in `LICENSE`.

Rebranding is supported, but required attribution must remain visible:

**Powered by Plaxtra**

Official repository: https://github.com/emircorp/Plaxtra

The license is intentionally attribution-focused and is not an OSI-approved open-source license. Third-party dependencies and assets remain under their own licenses.
