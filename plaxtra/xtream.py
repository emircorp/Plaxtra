from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urljoin
import httpx

@dataclass
class XtreamConfig:
    host: str
    username: str
    password: str
    https: bool = True

    @property
    def base_url(self) -> str:
        scheme = 'https' if self.https else 'http'
        return f'{scheme}://{self.host.strip().rstrip("/")}/'

class XtreamClient:
    def __init__(self, config: XtreamConfig, timeout: float = 20):
        self.config = config
        self.timeout = timeout

    def _request(self, action: str, **params):
        query = {'username': self.config.username, 'password': self.config.password, 'action': action, **params}
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            response = client.get(urljoin(self.config.base_url, 'player_api.php'), params=query)
            response.raise_for_status()
            return response.json()

    def server_info(self): return self._request('')
    def live_categories(self): return self._request('get_live_categories')
    def live_streams(self, category_id=None): return self._request('get_live_streams', **({'category_id': category_id} if category_id else {}))
    def vod_categories(self): return self._request('get_vod_categories')
    def vod_streams(self, category_id=None): return self._request('get_vod_streams', **({'category_id': category_id} if category_id else {}))
    def series_categories(self): return self._request('get_series_categories')
    def series(self, category_id=None): return self._request('get_series', **({'category_id': category_id} if category_id else {}))
    def series_info(self, series_id: int): return self._request('get_series_info', series_id=series_id)

    def live_url(self, stream_id, extension='m3u8'):
        return urljoin(self.config.base_url, f'live/{self.config.username}/{self.config.password}/{stream_id}.{extension}')
    def movie_url(self, stream_id, extension='mp4'):
        return urljoin(self.config.base_url, f'movie/{self.config.username}/{self.config.password}/{stream_id}.{extension}')
    def series_episode_url(self, stream_id, extension='mp4'):
        return urljoin(self.config.base_url, f'series/{self.config.username}/{self.config.password}/{stream_id}.{extension}')
