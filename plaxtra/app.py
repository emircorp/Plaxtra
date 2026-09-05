import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .db import init_db
from .api import router
from .features import router as features_router
from .xtream_api import router as xtream_router

BASE=Path(__file__).resolve().parent
init_db()
app=FastAPI(title='Plaxtra',version='0.4.0',docs_url='/api/docs',redoc_url='/api/redoc')
app.add_middleware(SessionMiddleware,secret_key=os.getenv('PLAXTRA_SECRET_KEY','change-me-in-production'),same_site='lax',https_only=os.getenv('PLAXTRA_SECURE_COOKIES','false').lower()=='true')
app.include_router(router)
app.include_router(features_router)
app.include_router(xtream_router)
static_dir=BASE/'static'; static_dir.mkdir(exist_ok=True)
app.mount('/static',StaticFiles(directory=static_dir),name='static')

HTML='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Plaxtra</title><link rel="stylesheet" href="/static/app.css"></head><body><nav><a class="brand" href="/">PLAXTRA</a><div class="links"><a href="/">Home</a><a href="/movies">Movies</a><a href="/series">Series</a><a href="/live">Live TV</a><a href="/search">Search</a><a href="/admin">Admin</a><a href="/login">Sign in</a></div></nav><main class="page">{body}</main><footer>Powered by Plaxtra · <a href="https://github.com/emircorp/Plaxtra">Official repository</a></footer></body></html>'''

def shell(title,body): return HTML.format(title=title,body=body)

@app.get('/',response_class=HTMLResponse)
def home(): return shell('Home','''<section class="hero"><small>SELF-HOSTED · REBRANDABLE</small><h1>Your media.<br><em>Your server.</em></h1><p>Movies, series and Live TV in one private streaming platform.</p><a class="button" href="/movies">Browse library</a></section><section><div class="section-head"><h2>Everything in one place</h2></div><div class="grid"><a href="/movies"><b>Movies</b><span>Film library</span></a><a href="/series"><b>Series</b><span>Seasons and episodes</span></a><a href="/live"><b>Live TV</b><span>M3U and HLS channels</span></a><a href="/admin"><b>Admin</b><span>Manage your server</span></a></div></section>''')

@app.get('/setup',response_class=HTMLResponse)
def setup_page(): return shell('Setup','''<div class="panel"><h1>First-run setup</h1><p>Create the first administrator account.</p><form onsubmit="setup(event)"><input id="u" placeholder="Username" required><input id="p" type="password" placeholder="Password (8+ characters)" minlength="8" required><button class="button">Create admin</button></form></div><script>async function setup(e){e.preventDefault();const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});if(r.ok)location='/login';else alert((await r.json()).detail||'Setup failed')}</script>''')

@app.get('/login',response_class=HTMLResponse)
def login_page(): return shell('Sign in','''<div class="panel"><h1>Sign in</h1><form onsubmit="login(event)"><input id="u" placeholder="Username" required><input id="p" type="password" placeholder="Password" required><button class="button">Sign in</button></form></div><script>async function login(e){e.preventDefault();const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});if(r.ok)location='/admin';else alert((await r.json()).detail||'Invalid credentials')}</script>''')

@app.get('/movies',response_class=HTMLResponse)
def movies_page(): return shell('Movies','''<div class="section-head"><div><small>LIBRARY</small><h1>Movies</h1></div><input id="q" placeholder="Search movies..."></div><div id="list" class="cards"></div><script>async function load(){const a=await (await fetch('/api/movies')).json(),v=q.value.toLowerCase();list.innerHTML=a.filter(x=>x.title.toLowerCase().includes(v)).map(x=>`<article class="card"><div class="poster" style="background-image:url('${x.poster_url||''}')"></div><div><b>${x.title}</b><span>${x.year||''} ${x.genre||''}</span>${x.stream_url?`<a class="button small" href="/watch?url=${encodeURIComponent(x.stream_url)}">Play</a>`:''}</div></article>`).join('')||'<p>No movies yet.</p>'}q.oninput=load;load()</script>''')

@app.get('/series',response_class=HTMLResponse)
def series_page(): return shell('Series','''<div class="section-head"><div><small>LIBRARY</small><h1>Series</h1></div><input id="q" placeholder="Search series..."></div><div id="list" class="cards"></div><script>async function load(){const a=await (await fetch('/api/series')).json(),v=q.value.toLowerCase();list.innerHTML=a.filter(x=>x.title.toLowerCase().includes(v)).map(x=>`<a class="card" href="/series/${x.id}"><div class="poster" style="background-image:url('${x.poster_url||''}')"></div><div><b>${x.title}</b><span>${x.year||''} ${x.genre||''}</span></div></a>`).join('')||'<p>No series yet.</p>'}q.oninput=load;load()</script>''')

@app.get('/series/{series_id}',response_class=HTMLResponse)
def series_detail_page(series_id:int): return shell('Series','''<div id="detail" class="panel">Loading…</div><script>fetch('/api/series/%s').then(r=>r.json()).then(x=>{detail.innerHTML=`<h1>${x.title}</h1><p>${x.synopsis||''}</p>`+x.seasons.map(s=>`<section><h2>Season ${s.season_number}</h2>`+s.episodes.map(e=>`<p><b>${e.episode_number}. ${e.title}</b> ${e.stream_url?`<a class="button small" href="/watch?url=${encodeURIComponent(e.stream_url)}">Play</a>`:''}</p>`).join('')+'</section>').join('')})</script>'''%series_id)

@app.get('/live',response_class=HTMLResponse)
def live_page(): return shell('Live TV','''<div class="section-head"><div><small>LIVE</small><h1>Channels</h1></div></div><div id="channels" class="cards"></div><script>fetch('/api/live').then(r=>r.json()).then(a=>channels.innerHTML=a.map(x=>`<article class="card"><div class="logo" style="background-image:url('${x.logo_url||''}')"></div><div><b>${x.number?x.number+' · ':''}${x.name}</b><span>${x.group}</span><a class="button small" href="/watch?url=${encodeURIComponent(x.stream_url)}">Watch</a></div></article>`).join('')||'<p>No channels imported.</p>')</script>''')

@app.get('/watch',response_class=HTMLResponse)
def watch(): return shell('Player','''<div class="player"><video id="video" controls autoplay playsinline></video><h1>Plaxtra Player</h1></div><script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js"></script><script>const url=new URLSearchParams(location.search).get('url')||'';const v=document.getElementById('video');if(window.Hls&&Hls.isSupported()){const h=new Hls();h.loadSource(url);h.attachMedia(v)}else v.src=url</script>''')

@app.get('/search',response_class=HTMLResponse)
def search_page(): return shell('Search','''<div class="panel"><h1>Search</h1><input id="q" autofocus placeholder="Search movies and series"><div id="r"></div></div><script>async function go(){const [m,s]=await Promise.all([fetch('/api/movies').then(r=>r.json()),fetch('/api/series').then(r=>r.json())]);const v=q.value.toLowerCase();r.innerHTML=[...m.map(x=>`<p>Movie · <b>${x.title}</b></p>`),...s.map(x=>`<p>Series · <b>${x.title}</b></p>`)].filter(x=>x.toLowerCase().includes(v)).join('')}q.oninput=go;go()</script>''')

@app.get('/admin',response_class=HTMLResponse)
def admin_page(): return shell('Admin','''<div class="section-head"><div><small>CONTROL CENTER</small><h1>Admin</h1></div><button class="button" onclick="logout()">Sign out</button></div><div class="admin-grid"><section class="panel"><h2>Add movie</h2><form onsubmit="movie(event)"><input id="mt" placeholder="Title" required><input id="my" type="number" placeholder="Year"><input id="mp" placeholder="Poster URL"><input id="ms" placeholder="Stream URL"><input id="mg" placeholder="Genre"><button class="button">Add movie</button></form></section><section class="panel"><h2>Xtream Codes</h2><form onsubmit="xtreamTest(event)"><input id="xh" placeholder="Host / domain" required><input id="xu" placeholder="Username" required><input id="xp" type="password" placeholder="Password" required><label><input id="xhttps" type="checkbox" checked> HTTPS</label><div class="row"><button class="button" type="submit">Test connection</button><button class="button secondary" type="button" onclick="xtreamImport()">Import all</button></div></form><p id="xstatus" class="muted">Imports Live TV, VOD and Series → Seasons → Episodes.</p></section><section class="panel"><h2>Import M3U</h2><form onsubmit="playlist(event)"><input id="pn" placeholder="Playlist name" required><input id="pu" placeholder="https://example.com/playlist.m3u" required><button class="button">Import playlist</button></form></section></div><script>async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(r.status===401||r.status===403){location='/login';throw Error('Authentication required')}const j=await r.json();if(!r.ok)throw Error(j.detail||'Request failed');return j}function xtreamData(){return {host:xh.value,username:xu.value,password:xp.value,https:xhttps.checked}}async function xtreamTest(e){e.preventDefault();xstatus.textContent='Testing…';try{const x=await post('/api/admin/xtream/test',xtreamData());xstatus.textContent='Connected. Server information received.';console.log(x.server_info)}catch(x){xstatus.textContent=x.message}}async function xtreamImport(){xstatus.textContent='Importing…';try{const x=await post('/api/admin/xtream/import',xtreamData());const c=x.counts;xstatus.textContent=`Imported: ${c.live} live · ${c.movies} movies · ${c.series} series · ${c.seasons} seasons · ${c.episodes} episodes`}catch(x){xstatus.textContent=x.message}}async function movie(e){e.preventDefault();try{await post('/api/admin/movies',{title:mt.value,year:my.value?+my.value:null,poster_url:mp.value,stream_url:ms.value,genre:mg.value});alert('Movie added')}catch(x){alert(x.message)}}async function playlist(e){e.preventDefault();try{const x=await post('/api/admin/playlists/import',{name:pn.value,source_url:pu.value});alert(`Imported ${x.imported} channels`)}catch(x){alert(x.message)}}async function logout(){await fetch('/api/auth/logout',{method:'POST'});location='/'}</script>''')
