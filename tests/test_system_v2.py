import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from crumble.api import create_app
from crumble.demo import make
from crumble.embeddings import Encoder
from crumble.ingest import ingest
from crumble.jobs import work
from crumble.retrieval import build
from crumble.reviews import edit_part
from crumble.security import SESSION_MAX_AGE, session_value, valid_session
from crumble.store import Store


@pytest.fixture
def workspace(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    work(store, encoder)
    build(store, encoder)
    return store


def photo(colour="orange"):
    b = io.BytesIO()
    Image.new("RGB", (30, 40), colour).save(b, "PNG")
    return b.getvalue()


def test_unicode_credentials_are_rejected_without_server_error(workspace):
    client = TestClient(create_app(workspace.root, token="x" * 32))
    assert client.post("/api/session", json={"token": "incorrect \u00e9"}).status_code == 401
    assert client.get("/api/status", headers={"Authorization": b"Bearer incorrect \xe9"}).status_code == 401
    # Unicode tokens are valid credentials too; Unicode handling is not a lossy ASCII conversion.
    token = "\u00e9" * 32
    client = TestClient(create_app(workspace.root, token=token))
    assert client.post("/api/session", json={"token": token}).status_code == 200
    assert client.get("/api/status").status_code == 200


def test_sessions_expire_are_signed_and_reject_rotation(workspace, monkeypatch):
    token = "x" * 32
    value = session_value(token, timestamp=100)
    assert valid_session(value, token, 100)
    assert valid_session(value, token, 100 + SESSION_MAX_AGE - 1)
    assert not valid_session(value, token, 100 + SESSION_MAX_AGE)
    assert not valid_session(value, token, 99)
    assert not valid_session(value, "y" * 32, 101)
    assert not valid_session(value[:-1] + ("0" if value[-1] != "0" else "1"), token, 101)
    monkeypatch.setattr("crumble.security.time.time", lambda: 100 + SESSION_MAX_AGE)
    client = TestClient(create_app(workspace.root, token=token))
    client.cookies.set("crumble_session", value)
    assert client.get("/api/status").status_code == 401


def test_cookie_secure_can_be_set_for_https_reverse_proxy(workspace, monkeypatch):
    monkeypatch.setenv("CRUMBLE_COOKIE_SECURE", "true")
    client = TestClient(create_app(workspace.root, token="x" * 32))
    response = client.post("/api/session", json={"token": "x" * 32})
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    monkeypatch.setenv("CRUMBLE_COOKIE_SECURE", "unexpected")
    with pytest.raises(ValueError, match="true or false"):
        create_app(workspace.root)


def test_read_only_visitors_can_end_their_browser_session(workspace):
    client = TestClient(create_app(workspace.root, token="x" * 32, read_only=True))
    assert client.post("/api/session", json={"token": "x" * 32}).status_code == 200
    assert client.get("/api/status").status_code == 200
    assert client.delete("/api/session").status_code == 200
    assert client.get("/api/status").status_code == 401


def test_read_only_blocks_persistent_writes_before_parsing(workspace):
    client = TestClient(create_app(workspace.root, read_only=True))
    before = workspace.summary()
    for method, path in [
        ("post", "/api/ingest"),
        ("patch", "/api/products/dress-a/parts"),
        ("post", "/api/reviews"),
        ("post", "/api/products/dress-a/infer"),
        ("get", "/api/export"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 403, response.text
    assert workspace.summary() == before
    status = client.get("/api/status").json()
    assert status["read_only"] is True and status["capabilities"]["write"] is False
    assert client.get("/api/compare?a=dress-a&b=dress-b").status_code == 200
    assert client.post("/api/search/photo", files={"file": ("p.png", photo())}).status_code == 200
    assert workspace.summary() == before
    assert client.post("/api/session", json={"token": ""}).status_code == 200
    assert client.delete("/api/session").status_code == 200


def test_public_search_rate_and_upload_bounds(workspace):
    client = TestClient(create_app(workspace.root, read_only=True))
    for _ in range(30):
        assert client.get("/api/products/dress-a/similar").status_code == 200
    response = client.get("/api/products/dress-a/similar")
    assert response.status_code == 429 and response.headers["retry-after"] == "60"
    client = TestClient(create_app(workspace.root, read_only=True))
    response = client.post("/api/search/photo", files={"file": ("p.png", b"x" * (5 * 1024 * 1024 + 1))})
    assert response.status_code == 400 and "5 MB" in response.json()["detail"]
    b = io.BytesIO()
    Image.new("RGB", (2001, 2000)).save(b, "PNG")
    response = client.post("/api/search/photo", files={"file": ("large.png", b.getvalue())})
    assert response.status_code == 400 and "4 megapixels" in response.json()["detail"]


def test_inference_uses_selected_view_and_rejects_stale_or_foreign_image(workspace, monkeypatch):
    ingest(
        workspace, {"id": "multi", "title": "Top", "rights": "Test fixture"}, [photo("red"), photo("blue")]
    )
    p = workspace.product("multi")
    app = create_app(workspace.root)
    seen = []
    monkeypatch.setattr(app.state.encoder, "parts", lambda image: seen.append(image.getpixel((0, 0))) or {})
    client = TestClient(app)
    response = client.post(
        "/api/products/multi/infer", params={"asset_id": p["images"][1], "snapshot": p["snapshot"]}
    )
    assert response.status_code == 200
    assert response.json()["image"] == p["images"][1]
    assert seen[0][2] > seen[0][0]
    assert (
        client.post(
            "/api/products/multi/infer", params={"asset_id": "0" * 64, "snapshot": p["snapshot"]}
        ).status_code
        == 400
    )
    edit_part(
        workspace,
        "multi",
        {
            "snapshot": p["snapshot"],
            "field": "neckline",
            "reviewer": "Test",
            "claim": {"state": "verified", "values": ["square"], "source": "Test fixture"},
        },
    )
    assert (
        client.post(
            "/api/products/multi/infer", params={"asset_id": p["images"][1], "snapshot": p["snapshot"]}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "title,category,parts,expected,state",
    [
        ("Style 001", "dress", {}, ["dress"], "stated"),
        ("Red top", "trousers", {}, ["top", "trousers"], "conflicting"),
        ("Red top", "shirt", {}, ["top"], "stated"),
        ("Wool cardigan", "knitwear", {}, ["knitwear"], "stated"),
        (
            "Red top",
            "top",
            {"category": {"state": "verified", "values": ["skirt"], "source": "Test"}},
            ["skirt", "top"],
            "conflicting",
        ),
        ("Style 001", "Custom category", {}, ["custom category"], "stated"),
    ],
)
def test_category_sources_are_preserved(workspace, title, category, parts, expected, state):
    ingest(
        workspace,
        {"id": "new", "title": title, "category": category, "parts": parts, "rights": "Test fixture"},
        [photo()],
    )
    f = workspace.product("new")["structure"]["fields"]["category"]
    assert f["values"] == expected and f["state"] == state
    assert any(e["source"] == "metadata.category" and e["quote"] == category for e in f["evidence"])
