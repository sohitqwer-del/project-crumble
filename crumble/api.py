# SPDX-License-Identifier: Apache-2.0
import json
import os
import threading
import time
from collections import deque
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
from .security import (
    SESSION_MAX_AGE,
    BodyLimit,
    authenticated,
    boolean_env,
    same_origin,
    secure_equal,
    session_value,
)
from .settings import initialise, library
from .store import Store


def create_app(workspace="work", token=None, read_only=None):
    token = token if token is not None else os.environ.get("CRUMBLE_TOKEN", "")
    if token and len(token) < 32:
        raise ValueError("CRUMBLE_TOKEN must contain at least 32 characters")
    read_only = boolean_env("CRUMBLE_READ_ONLY") if read_only is None else bool(read_only)
    cookie_secure = boolean_env("CRUMBLE_COOKIE_SECURE") if "CRUMBLE_COOKIE_SECURE" in os.environ else None
    recent_searches = deque()
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
        if read_only:
            mutable = request.method not in ("GET", "HEAD", "OPTIONS")
            safe_session = request.url.path == "/api/session" and request.method in ("POST", "DELETE")
            safe_search = request.url.path == "/api/search/photo" and request.method == "POST"
            if (mutable and not safe_session and not safe_search) or request.url.path == "/api/export":
                return JSONResponse(
                    {"detail": "This public demo is read-only. Use your own workspace to save changes."},
                    status_code=403,
                )
            is_search = request.url.path.startswith("/api/search/") or request.url.path.endswith("/similar")
            if is_search:
                stamp = time.monotonic()
                while recent_searches and recent_searches[0] <= stamp - 60:
                    recent_searches.popleft()
                if len(recent_searches) >= 30:
                    return JSONResponse(
                        {"detail": "Public demo search limit reached. Try again in a minute."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
                recent_searches.append(stamp)
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
        if not isinstance(supplied, str) or (token and not secure_equal(token, supplied)):
            raise HTTPException(401, "Invalid access token")
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "crumble_session",
            session_value(token),
            httponly=True,
            samesite="strict",
            secure=cookie_secure if cookie_secure is not None else request.url.scheme == "https",
            max_age=SESSION_MAX_AGE,
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
            "read_only": read_only,
            "capabilities": {
                "write": not read_only,
                "infer": not read_only and encoder.name == "fashion",
                "photo_search": True,
                "text_search": encoder.name == "fashion",
            },
            "public_search_limit_per_minute": 30 if read_only else None,
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
        maximum = 5 * 1024 * 1024 if read_only else MAX_BYTES
        blob = file.file.read(maximum + 1)
        if len(blob) > maximum:
            raise ValueError(
                "Public demo photos must be at most 5 MB" if read_only else "Image exceeds 20 MB"
            )
        with decode(blob) as image:
            if read_only and image.width * image.height > 4_000_000:
                raise ValueError("Public demo photos must be at most 4 megapixels")
            with lock:
                return search.query(
                    encoder.images([image])[0], min(limit, 20) if read_only else limit, category
                )

    @app.get("/api/search/text")
    def text(q: str = Query(..., min_length=1, max_length=1000), limit: int = Query(20, ge=1, le=100)):
        with lock:
            return search.query(encoder.texts([q])[0], min(limit, 20) if read_only else limit)

    @app.get("/api/products/{pid}/similar")
    def similar(pid: str):
        p = store.product(pid)
        with Image.open(store.asset_path(p["images"][0])) as im, lock:
            return search.query(encoder.images([im.convert("RGB")])[0], exclude=pid)

    @app.post("/api/products/{pid}/infer")
    def infer(pid: str, asset_id: str = Query("", max_length=64), snapshot: str = Query("", max_length=64)):
        p = store.product(pid)
        if snapshot and snapshot != p["snapshot"]:
            raise HTTPException(409, "This garment changed. Reload before requesting proposals.")
        selected = asset_id or p["images"][0]
        if selected not in p["images"]:
            raise ValueError("The selected image does not belong to this garment's current snapshot")
        with Image.open(store.asset_path(selected)) as im, lock:
            proposed = encoder.parts(im.convert("RGB"))
        if store.product(pid)["snapshot"] != p["snapshot"]:
            raise HTTPException(409, "This garment changed during inference. Reload and try again.")
        return {"snapshot": p["snapshot"], "image": selected, "proposals": proposed, "persisted": False}

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
