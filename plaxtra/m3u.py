from dataclasses import dataclass, field
import re
from urllib.parse import urlparse

@dataclass
class M3UItem:
    name: str
    url: str
    tvg_id: str = ""
    tvg_name: str = ""
    logo: str = ""
    group: str = "General"
    language: str = ""
    country: str = ""
    channel_number: str = ""
    radio: str = ""
    catchup: str = ""
    catchup_source: str = ""
    catchup_days: str = ""
    attrs: dict[str, str] = field(default_factory=dict)


def _attrs(text: str) -> dict[str, str]:
    # M3U attributes may contain spaces inside quoted values.
    body = text.split(':', 1)[1] if ':' in text else text
    pattern = re.compile(r'''([A-Za-z0-9_-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+))''')
    return {m.group(1).lower(): next(v for v in m.groups()[1:] if v is not None) for m in pattern.finditer(body)}


def parse_m3u(text: str) -> list[M3UItem]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    result: list[M3UItem] = []
    pending: tuple[str, dict[str, str]] | None = None
    for line in lines:
        if line.upper().startswith('#EXTINF:'):
            meta, _, name = line.partition(',')
            attrs = _attrs(meta)
            display_name = name.strip() or attrs.get('tvg-name', 'Untitled')
            pending = (display_name, attrs)
        elif not line.startswith('#') and pending:
            name, attrs = pending
            result.append(M3UItem(
                name=name,
                url=line,
                tvg_id=attrs.get('tvg-id', ''),
                tvg_name=attrs.get('tvg-name', name),
                logo=attrs.get('tvg-logo', ''),
                group=attrs.get('group-title', 'General'),
                language=attrs.get('tvg-language', attrs.get('language', '')),
                country=attrs.get('tvg-country', attrs.get('country', '')),
                channel_number=attrs.get('tvg-chno', attrs.get('channel-number', '')),
                radio=attrs.get('radio', ''),
                catchup=attrs.get('catchup', ''),
                catchup_source=attrs.get('catchup-source', ''),
                catchup_days=attrs.get('catchup-days', ''),
                attrs=attrs,
            ))
            pending = None
    return result


def valid_remote_url(url: str) -> bool:
    p = urlparse(url)
    return p.scheme in {'http', 'https'} and bool(p.hostname)
