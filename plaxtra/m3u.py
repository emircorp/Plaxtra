from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class M3UItem:
    name: str
    url: str
    tvg_id: str = ""
    logo: str = ""
    group: str = "General"

def _attrs(text: str) -> dict[str,str]:
    out = {}
    for token in text.split(' '):
        if '=' in token:
            k,v = token.split('=',1); out[k.strip()] = v.strip().strip('"')
    return out

def parse_m3u(text: str) -> list[M3UItem]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    result=[]; pending=None
    for line in lines:
        if line.upper().startswith('#EXTINF:'):
            meta, _, name = line.partition(',')
            attrs=_attrs(meta)
            pending=(name.strip() or attrs.get('tvg-name','Untitled'), attrs)
        elif not line.startswith('#') and pending:
            name, attrs=pending
            result.append(M3UItem(name=name,url=line,tvg_id=attrs.get('tvg-id',''),logo=attrs.get('tvg-logo',''),group=attrs.get('group-title','General')))
            pending=None
    return result

def valid_remote_url(url: str) -> bool:
    p=urlparse(url)
    return p.scheme in {'http','https'} and bool(p.hostname)
