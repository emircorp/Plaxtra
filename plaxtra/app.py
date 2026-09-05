from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .db import init_db
from .api import router

BASE = Path(__file__).resolve().parent
init_db()
app = FastAPI(title="Plaxtra", version="0.2.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(SessionMiddleware, secret_key="change-me-in-production", same_site="lax", https_only=False)
app.include_router(router)
static_dir=BASE/"static"; static_dir.mkdir(exist_ok=True)
app.mount("/static",StaticFiles(directory=static_dir),name="static")

PAGE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Plaxtra</title><link rel="stylesheet" href="/static/app.css"></head><body><nav><a class="brand" href="/">PLAXTRA</a><div class="links"><a href="/">Home</a><a href="/movies">Movies</a><a href="/live">Live TV</a><a href="/search">Search</a><a href="/login">Sign in</a></div></nav><main><section class="hero"><div><small>SELF-HOSTED · REBRANDABLE</small><h1>Your media.<br><em>Your server.</em></h1><p>Movies, series and Live TV in one private streaming platform.</p><div><a class="button" href="/movies">Browse library</a><a class="ghost" href="/live">Live TV</a></div></div></section><section><div class="section-head"><h2>Everything in one place</h2></div><div class="grid"><a href="/movies"><b>Movies</b><span>Browse your film library</span></a><a href="/movies"><b>Series</b><span>Seasons and episodes</span></a><a href="/live"><b>Live TV</b><span>M3U and HLS channels</span></a><a href="/admin"><b>Admin</b><span>Manage your server</span></a></div></section></main><footer>Powered by Plaxtra · <a href="https://github.com/emircorp/Plaxtra">Official repository</a></footer></body></html>'''

def shell(title, body): return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Plaxtra</title><link rel="stylesheet" href="/static/app.css"></head><body><nav><a class="brand" href="/">PLAXTRA</a><div class="links"><a href="/">Home</a><a href="/movies">Movies</a><a href="/live">Live TV</a><a href="/login">Sign in</a></div></nav><main class="page">{body}</main><footer>Powered by Plaxtra · <a href="https://github.com/emircorp/Plaxtra">Official repository</a></footer></body></html>'''

@app.get('/',response_class=HTMLResponse)
def home(): return PAGE

@app.get('/setup',response_class=HTMLResponse)
def setup_page(): return shell('Setup','''<div class="panel"><h1>First-run setup</h1><p>Create the first administrator account.</p><form onsubmit="setup(event)"><input id="u" placeholder="Username" required><input id="p" type="password" placeholder="Password (8+ characters)" required minlength="8"><button class="button">Create admin</button></form></div><script>async function setup(e){e.preventDefault();let r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let j=await r.json();if(r.ok)location='/login';else alert(j.detail||'Setup failed')}</script>''')

@app.get('/login',response_class=HTMLResponse)
def login_page(): return shell('Sign in','''<div class="panel"><h1>Sign in</h1><form onsubmit="login(event)"><input id="u" placeholder="Username" required><input id="p" type="password" placeholder="Password" required><button class="button">Sign in</button></form></div><script>async function login(e){e.preventDefault();let r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let j=await r.json();if(r.ok)location='/admin';else alert(j.detail||'Invalid credentials')}</script>''')

@app.get('/movies',response_class=HTMLResponse)
def movies_page(): return shell('Movies','''<div class="section-head"><div><small>LIBRARY</small><h1>Movies</h1></div><input id="q" placeholder="Search movies..." oninput="load()"></div><div id="list" class="cards"></div><script>async function load(){let a=await (await fetch('/api/movies')).json(),q=(document.getElementById('q').value||'').toLowerCase();list.innerHTML=a.filter(x=>x.title.toLowerCase().includes(q)).map(x=>`<article class="card"><div class="poster" style="background-image:url('${x.poster_url||''}')"></div><div><b>${x.title}</b><span>${x.year||''} ${x.genre||''}</span>${x.stream_url?`<a class="button small" href="/watch?url=${encodeURIComponent(x.stream_url)}">Play</a>`:''}</div></article>`).join('')||'<p>No movies yet.</p>'}load()</script>''')

@app.get('/live',response_class=HTMLResponse)
def live_page(): return shell('Live TV','''<div class="section-head"><div><small>LIVE</small><h1>Channels</h1></div></div><div id="channels" class="cards"></div><script>async function load(){let a=await (await fetch('/api/live')).json();channels.innerHTML=a.map(x=>`<article class="card"><div class="logo" style="background-image:url('${x.logo_url||''}')"></div><div><b>${x.number?x.number+' · ':''}${x.name}</b><span>${x.group}</span><a class="button small" href="/watch?url=${encodeURIComponent(x.stream_url)}">Watch</a></div></article>`).join('')||'<p>No channels imported.</p>'}load()</script>''')

@app.get('/watch',response_class=HTMLResponse)
def watch(request:Request):
    from urllib.parse import quote
    url=request.query_params.get('url','')
    return shell('Player',f'''<div class="player"><video controls autoplay playsinline src="{url}"></video><h1>Plaxtra Player</h1><p>If the stream is HLS and your browser does not support it natively, an HLS.js integration can be enabled in the player frontend.</p></div>''')

@app.get('/admin',response_class=HTMLResponse)
def admin_page(): return shell('Admin','''<div class="section-head"><div><small>CONTROL CENTER</small><h1>Admin</h1></div><button class="button" onclick="logout()">Sign out</button></div><div class="admin-grid"><section class="panel"><h2>Add movie</h2><form onsubmit="movie(event)"><input id="mt" placeholder="Title" required><input id="my" type="number" placeholder="Year"><input id="mp" placeholder="Poster URL"><input id="ms" placeholder="Stream URL"><input id="mg" placeholder="Genre"><button class="button">Add movie</button></form></section><section class="panel"><h2>Add channel</h2><form onsubmit="channel(event)"><input id="cn" placeholder="Channel name" required><input id="cs" placeholder="Stream URL" required><input id="cg" placeholder="Group"><input id="cl" placeholder="Logo URL"><button class="button">Add channel</button></form></section></div><script>async function api(path,body){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(r.status===401||r.status===403)location='/login';if(!r.ok)alert((await r.json()).detail||'Request failed');else alert('Saved')}async function movie(e){e.preventDefault();await api('/api/admin/movies',{title:mt.value,year:my.value?+my.value:null,poster_url:mp.value,stream_url:ms.value,genre:mg.value})}async function channel(e){e.preventDefault();await api('/api/admin/channels',{name:cn.value,stream_url:cs.value,group_name:cg.value||'General',logo_url:cl.value})}async function logout(){await fetch('/api/auth/logout',{method:'POST'});location='/'}</script>''')

@app.get('/search',response_class=HTMLResponse)
def search_page(): return shell('Search','''<div class="panel"><h1>Search</h1><input id="q" autofocus placeholder="Search your library"><div id="r"></div></div><script>q.oninput=async()=>{let a=await (await fetch('/api/movies')).json(),v=q.value.toLowerCase();r.innerHTML=a.filter(x=>x.title.toLowerCase().includes(v)).map(x=>`<p><b>${x.title}</b> ${x.year||''}</p>`).join('')}</script>''')
