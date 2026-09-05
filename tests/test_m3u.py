from plaxtra.m3u import parse_m3u, valid_remote_url

def test_parse_m3u():
    text='''#EXTM3U\n#EXTINF:-1 tvg-id="news" tvg-logo="https://x/logo.png" group-title="News",Example News\nhttps://example.com/live.m3u8'''
    x=parse_m3u(text)[0]
    assert x.name=='Example News'; assert x.tvg_id=='news'; assert x.group=='News'; assert x.url.endswith('.m3u8')

def test_url_validation():
    assert valid_remote_url('https://example.com/a.m3u8')
    assert not valid_remote_url('file:///tmp/a')
