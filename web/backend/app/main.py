from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST, get_settings
from .bootstrap import ensure_bootstrap_admin
from .database import init_db
from .routers import admin, auth, cases, settings as settings_router, tasks
from .services.word_service import shutdown_word

logger = logging.getLogger("v6")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    await init_db()
    await ensure_bootstrap_admin()
    yield
    shutdown_word()


app = FastAPI(title="案件归档 V6", version="6.0.0", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(tasks.router)
app.include_router(settings_router.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "capabilities": _settings.capabilities}


@app.get("/api/capabilities")
async def capabilities():
    return _settings.capabilities


if FRONTEND_DIST.exists():
    @app.get("/", include_in_schema=False)
    async def index_html():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

if FRONTEND_DIST.exists():
    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all_spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        target = FRONTEND_DIST / (path or "index.html")
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
