import json
from plaxtra.m3u import parse_m3u

def test_m3u_preserves_extended_metadata():
    text='''#EXTM3U
#EXTINF:-1 tvg-id="news" tvg-name="News HD" tvg-logo="https://example.com/logo.png" group-title="News World" tvg-language="English" tvg-country="US" tvg-chno="101" catchup="append" catchup-days="7",News HD
https://example.com/live.m3u8'''
    item=parse_m3u(text)[0]
    assert item.group == 'News World'
    assert item.language == 'English'
    assert item.country == 'US'
    assert item.channel_number == '101'
    assert item.attrs['catchup'] == 'append'
    assert item.attrs['catchup-days'] == '7'

def test_metadata_json_is_serializable():
    item=parse_m3u('#EXTM3U\n#EXTINF:-1 tvg-id="x",Test\nhttps://example.com/a')[0]
    payload=json.dumps(item.attrs, ensure_ascii=False)
    assert 'tvg-id' in payload
