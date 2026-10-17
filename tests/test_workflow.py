import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from crumble.api import create_app
from crumble.demo import make
from crumble.embeddings import Encoder
from crumble.ingest import decode, import_file
from crumble.jobs import work
from crumble.queue import pending, populate
from crumble.retrieval import Search, build
from crumble.reviews import comparison, edit_part, save_review
from crumble.settings import library
from crumble.store import Store


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    work(store, encoder)
    build(store, encoder)
    return store, encoder


def review_data(store):
    d = comparison(store, "dress-a", "dress-b", library(store))
    return {
        "a": "dress-a",
        "b": "dress-b",
        "snapshot_a": d["a"]["snapshot"],
        "snapshot_b": d["b"]["snapshot"],
        "relation": "modified_design",
        "changed": ["sleeve_length", "pockets"],
        "reviewer": "Test reviewer",
        "smv_library_hash": d["smv"]["library_hash"],
        "smv_decision": "needs_time_study",
    }


def test_demo_search_reviews_and_history(setup):
    store, encoder = setup
    app = TestClient(create_app(store.root))
    assert app.get("/").status_code == 200
    assert app.get("/docs").status_code == 200
    p = store.product("dress-a")
    blob = store.asset_path(p["images"][0]).read_bytes()
    result = app.post("/api/search/photo", files={"file": ("dress.jpg", blob, "image/jpeg")})
    assert result.status_code == 200, result.text
    assert result.json()["items"][0]["product"]["id"] == "dress-a"
    d = app.get("/api/compare?a=dress-a&b=dress-b").json()
    assert set(d["comparison"]["different"]) == {"sleeve_length", "pockets"}
    assert d["smv"]["mapped_delta"] == {"low": 2.1, "high": 3.5}
    assert d["smv"]["new_total_smv"] is None
    assert d["smv"]["illustrative"] is True
    assert app.post("/api/reviews", json=review_data(store)).status_code == 200
    history = app.get("/api/products/dress-a/history").json()
    assert len(history["reviewed_relationships"]) == 1
    exported = [json.loads(x) for x in app.get("/api/export").text.splitlines()]
    assert exported[0]["time_library"]["version"] == "crumble-demo/1"
    assert "copy" not in exported[0]["relation"]


def test_stale_reviews_and_corrections_are_rejected(setup):
    store, _ = setup
    payload = review_data(store)
    p = store.product("dress-a")
    edit = {
        "snapshot": p["snapshot"],
        "field": "neckline",
        "reviewer": "Test reviewer",
        "claim": {"state": "verified", "values": ["v-neck"], "source": "Front image checked"},
    }
    edit_part(store, p["id"], edit)
    with pytest.raises(ValueError, match="changed"):
        edit_part(store, p["id"], edit)
    with pytest.raises(ValueError, match="changed"):
        save_review(store, payload, library(store))
    assert store.summary()["reviews"] == 0
    assert store.summary()["snapshots"] == 11


def test_auth_csrf_and_input_validation(setup):
    store, _ = setup
    token = "test-" * 8
    c = TestClient(create_app(store.root, token=token))
    assert c.get("/api/status").status_code == 401
    assert c.get("/api/status", headers={"Authorization": "Bearer " + token}).status_code == 200
    assert (
        c.post("/api/session", json={"token": token}, headers={"Origin": "https://evil.invalid"}).status_code
        == 403
    )
    r = c.post("/api/session", json={"token": token})
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/status").status_code == 200
    assert (
        c.post("/api/search/photo", files={"file": ("bad.jpg", b"invalid", "image/jpeg")}).status_code == 400
    )
    assert c.get("/api/products/missing").status_code == 404
    assert c.get("/api/status", headers={"Host": "evil.invalid"}).status_code == 400
    invalid = review_data(store)
    invalid["relation"] = "same_visible_design"
    assert c.post("/api/reviews", json=invalid).status_code == 422
    assert (
        c.post("/api/ingest", data={"metadata": "{"}, files={"files": ("x.jpg", b"bad")}).status_code == 400
    )


def test_model_generation_integrity_and_empty_rebuild(setup):
    store, encoder = setup
    search = Search(store, encoder)
    search.load()
    active = store.root / "indexes" / encoder.id / "active.json"
    old = active.read_bytes()
    with store.connect() as c:
        c.execute("DELETE FROM vectors")
    with pytest.raises(ValueError, match="No vectors"):
        build(store, encoder)
    assert active.read_bytes() == old
    folder = active.parent / search.manifest["generation"]
    with (folder / "vectors.npy").open("r+b") as f:
        f.seek(-1, 2)
        f.write(b"\xff")
    with pytest.raises(ValueError, match="checksum"):
        Search(store, encoder).load()


def test_bad_encoder_retries_and_restart_recovery(tmp_path):
    store = Store(tmp_path / "w")
    make(store)

    class Broken(Encoder):
        def images(self, images):
            raise ValueError("intentional failure")

    encoder = Broken()
    work(store, encoder)
    with store.connect() as c:
        states = c.execute("SELECT status,attempts FROM jobs").fetchall()
    assert all(r["status"] == "error" and r["attempts"] == 3 for r in states)
    good = Encoder()
    assert work(store, good, retry=True)["completed"] == 10
    assert work(store, good)["completed"] == 0


def test_queue_dedup_and_review_consumption(setup):
    store, encoder = setup
    search = Search(store, encoder)
    first = populate(store, search, 10)
    assert first["added"] > 0
    assert populate(store, search, 10)["added"] == 0
    pair = pending(store)["items"][0]
    d = comparison(store, pair["a"]["id"], pair["b"]["id"], library(store))
    payload = {
        "a": d["a"]["id"],
        "b": d["b"]["id"],
        "snapshot_a": d["a"]["snapshot"],
        "snapshot_b": d["b"]["snapshot"],
        "relation": "unsure",
        "reviewer": "Test reviewer",
        "smv_library_hash": d["smv"]["library_hash"],
    }
    n = len(pending(store)["items"])
    save_review(store, payload, library(store))
    assert len(pending(store)["items"]) == n - 1


def test_streaming_import_paths_rights_and_resume(tmp_path):
    store = Store(tmp_path / "w")
    root = tmp_path / "photos"
    root.mkdir()
    im = Image.new("RGB", (30, 40), "blue")
    im.save(root / "photo.png")
    manifest = tmp_path / "input.jsonl"
    product = {"id": "a", "title": "Blue top", "rights": "Owned", "images": ["photo.png"]}
    manifest.write_text(json.dumps(product) + "\n")
    assert import_file(store, manifest, root)["ok"] == 1
    p = store.product("a")
    edit_part(
        store,
        "a",
        {
            "snapshot": p["snapshot"],
            "field": "neckline",
            "reviewer": "Test reviewer",
            "claim": {"state": "verified", "values": ["square"], "source": "Image"},
        },
    )
    assert import_file(store, manifest, root)["unchanged"] == 1
    assert store.product("a")["structure"]["fields"]["neckline"]["state"] == "verified"
    product["images"] = ["../outside.png"]
    im.save(tmp_path / "outside.png")
    manifest.write_text(json.dumps(product) + "\n")
    assert import_file(store, manifest, root)["error"] == 1
    product["images"] = ["photo.png"]
    product.pop("rights")
    manifest.write_text(json.dumps(product) + "\n")
    assert import_file(store, manifest, root)["error"] == 1


def test_unknown_and_malformed_images():
    with pytest.raises(ValueError):
        decode(b"")
    with pytest.raises(ValueError):
        decode(b"not an image")
