# SPDX-License-Identifier: Apache-2.0
import json
import os
import secrets
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__, reviews
from .embeddings import Encoder
from .ingest import MAX_BYTES, decode, ingest
from .jobs import enqueue
from .models import PartEdit, Review
from .retrieval import Search
from .security import BodyLimit, authenticated, same_origin, session_value
from .settings import initialise, library
from .store import Store


def create_app(workspace="work", token=None):
    token = token if token is not None else os.environ.get("CRUMBLE_TOKEN", "")
    if token and len(token) < 32:
        raise ValueError("CRUMBLE_TOKEN must contain at least 32 characters")
    store = Store(workspace)
    settings = initialise(store)
    encoder = Encoder(settings["encoder"], settings["device"])
    search, lock = Search(store, encoder), threading.RLock()
    app = FastAPI(title="Project Crumble", version=__version__, docs_url=None, redoc_url=None)
    app.state.store, app.state.encoder = store, encoder
    app.add_middleware(BodyLimit)
    hosts = os.environ.get("CRUMBLE_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    static = Path(__file__).parent / "static"

    @app.middleware("http")
    async def access(request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS") and not same_origin(request):
            return JSONResponse({"detail": "Cross-origin writes are not allowed"}, status_code=403)
        protected = request.url.path.startswith(("/api/", "/assets/")) and request.url.path != "/api/session"
        if protected and not authenticated(request, token):
            return JSONResponse({"detail": "Sign in with the workspace access token"}, status_code=401)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'",
            }
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Item not found"}, status_code=404)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.post("/api/session")
    async def login(request: Request):
        data = await request.json()
        supplied = data.get("token", "") if isinstance(data, dict) else ""
        if not isinstance(supplied, str) or (token and not secrets.compare_digest(token, supplied)):
            raise HTTPException(401, "Invalid access token")
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "crumble_session",
            session_value(token),
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=28800,
        )
        return response

    @app.delete("/api/session")
    def logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie("crumble_session")
        return response

    @app.get("/api/status")
    def status():
        try:
            with lock:
                search.load()
                index = search.manifest
        except ValueError:
            index = None
        return {
            **store.summary(),
            "encoder": encoder.spec,
            "index": index,
            "smv_library": library(store),
            "version": __version__,
        }

    @app.get("/api/queue")
    def queue(limit: int = Query(50, ge=1, le=100)):
        from .queue import pending

        return pending(store, limit)

    @app.get("/docs")
    def docs():
        return FileResponse(static / "api.html")

    @app.get("/api/products")
    def products(
        q: str = Query("", max_length=200),
        category: str = Query("", max_length=100),
        offset: int = Query(0, ge=0),
        limit: int = Query(30, ge=1, le=100),
    ):
        return store.listing(q, category, offset, limit)

    @app.get("/api/products/{pid}")
    def product(pid: str):
        return store.product(pid)

    @app.get("/assets/{asset_id}")
    def image(asset_id: str):
        path = store.asset_path(asset_id)
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/ingest")
    def upload(metadata: str = Form(..., max_length=50000), files: list[UploadFile] = File(...)):
        if not 1 <= len(files) <= 8:
            raise ValueError("Provide 1 to 8 images")
        blobs = [f.file.read(MAX_BYTES + 1) for f in files]
        result = ingest(store, json.loads(metadata), blobs)
        enqueue(store, encoder)
        return {**result, "embedding": "queued"}

    @app.post("/api/search/photo")
    def photo(
        file: UploadFile = File(...),
        category: str = Form("", max_length=100),
        limit: int = Form(20, ge=1, le=100),
    ):
        image = decode(file.file.read(MAX_BYTES + 1))
        with lock:
            return search.query(encoder.images([image])[0], limit, category)

    @app.get("/api/search/text")
    def text(q: str = Query(..., min_length=1, max_length=1000), limit: int = Query(20, ge=1, le=100)):
        with lock:
            return search.query(encoder.texts([q])[0], limit)

    @app.get("/api/products/{pid}/similar")
    def similar(pid: str):
        p = store.product(pid)
        with Image.open(store.asset_path(p["images"][0])) as im, lock:
            return search.query(encoder.images([im.convert("RGB")])[0], exclude=pid)

    @app.post("/api/products/{pid}/infer")
    def infer(pid: str):
        p = store.product(pid)
        with Image.open(store.asset_path(p["images"][0])) as im, lock:
            proposed = encoder.parts(im.convert("RGB"))
        return {"snapshot": p["snapshot"], "image": p["images"][0], "proposals": proposed, "persisted": False}

    @app.patch("/api/products/{pid}/parts")
    def edit(pid: str, payload: PartEdit):
        return reviews.edit_part(store, pid, payload.model_dump())

    @app.get("/api/compare")
    def compare(a: str, b: str):
        return reviews.comparison(store, a, b, library(store))

    @app.post("/api/reviews")
    def review(payload: Review):
        return reviews.save_review(store, payload.model_dump(), library(store))

    @app.get("/api/products/{pid}/history")
    def history(pid: str):
        return reviews.history(store, pid)

    @app.get("/api/export")
    def export():
        def generate():
            with store.connect() as c:
                for row in c.execute("SELECT payload,created FROM reviews ORDER BY created"):
                    yield json.dumps({"created": row["created"], **json.loads(row["payload"])}) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=crumble-reviews.jsonl"},
        )

    @app.get("/")
    def home():
        return FileResponse(static / "index.html")

    app.mount("/static", StaticFiles(directory=static), name="static")
    return app
