from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
app = FastAPI(title="Plaxtra", version="0.1.0")

static_dir = BASE / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/api/health")
def health():
    return {"status": "ok", "name": "Plaxtra", "version": "0.1.0"}

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Plaxtra</title><link rel='stylesheet' href='/static/app.css'></head><body><nav><strong>PLAXTRA</strong><span>Home</span><span>Movies</span><span>Series</span><span>Live TV</span><span>Search</span></nav><main><section class='hero'><div><small>SELF-HOSTED MEDIA PLATFORM</small><h1>Your media.<br><em>Your server.</em></h1><p>A clean, rebrandable streaming experience built to run locally with Python.</p><button>Explore library</button></div></section><section><h2>Plaxtra</h2><div class='grid'><article>Movies</article><article>Series</article><article>Live TV</article><article>Continue Watching</article></div></section></main><footer>Powered by Plaxtra · <a href='https://github.com/emircorp/Plaxtra'>GitHub</a></footer></body></html>"""
