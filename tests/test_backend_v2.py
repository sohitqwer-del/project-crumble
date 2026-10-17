import json

import numpy as np
import pytest

from crumble.demo import make
from crumble.embeddings import Encoder
from crumble.jobs import work
from crumble.queue import pending, populate
from crumble.retrieval import Search, build, needs_build, top_positions
from crumble.store import Store
from crumble.util import canonical, digest


class Tiny:
    dim = 2
    spec = {"provider": "test-vectors", "dim": 2}
    id = digest(spec)


def product(store, number, vector, category="top", identity=""):
    aid = format(number + 1, "064x")
    payload = {
        "id": f"p{number:05d}",
        "title": "Test garment",
        "brand": "Example",
        "category": category,
        "identity_group": identity,
        "images": [aid],
    }
    store.save(payload, digest(payload))
    with store.connect() as c:
        c.execute(
            "INSERT INTO vectors VALUES(?,?,?)",
            (
                aid,
                Tiny.id,
                np.asarray(vector, dtype="<f4").tobytes(),
            ),
        )
    return payload


def catalogue(tmp_path, size=400):
    store = Store(tmp_path / "workspace")
    for i in range(size):
        product(store, i, [1, 0])
    return store, Tiny()


def test_category_is_applied_before_shortlisting(tmp_path):
    store, encoder = catalogue(tmp_path)
    product(store, 500, [0.7, 0.7], category="dress")
    build(store, encoder)
    result = Search(store, encoder).query([1, 0], limit=1, category="dress")
    assert [r["product"]["id"] for r in result["items"]] == ["p00500"]
    assert result["search_backend"] == "exact_filtered"
    assert result["approximate"] is False
    assert not result["filter_may_limit_results"]


def test_grouping_expands_a_shortlist_crowded_by_one_identity(tmp_path):
    store, encoder = catalogue(tmp_path)
    with store.connect() as c:
        rows = c.execute("SELECT id,snapshot FROM products").fetchall()
    for row in rows:
        p = store.snapshot(row["snapshot"])
        p["identity_group"] = "regional-family"
        store.save(p, "new-" + p["id"])
    product(store, 500, [0.7, 0.7], identity="other-family")
    build(store, encoder)
    result = Search(store, encoder).query([1, 0], limit=2, group=True)
    assert len(result["items"]) == 2
    assert result["items"][1]["product"]["id"] == "p00500"
    assert result["candidates_searched"] == 401


def test_stale_index_assets_do_not_hide_current_products(tmp_path):
    store, encoder = catalogue(tmp_path)
    product(store, 500, [0.7, 0.7])
    build(store, encoder)
    with store.connect() as c:
        c.execute("DELETE FROM product_assets WHERE product_id!='p00500'")
    result = Search(store, encoder).query([1, 0], limit=1)
    assert [r["product"]["id"] for r in result["items"]] == ["p00500"]


def test_partial_topk_is_deterministic_on_boundary_ties():
    scores = np.array([0.9, 0.8, 0.8, 0.8, 0.2])
    positions = np.array([3, 8, 2, 5, 1])
    selected = top_positions(scores, positions, 3)
    assert positions[selected].tolist() == [3, 2, 5]


def test_request_keeps_one_generation_during_reload(tmp_path, monkeypatch):
    store, encoder = catalogue(tmp_path, size=2)
    old = build(store, encoder)
    search = Search(store, encoder)
    original = search._nearest
    changed = False

    def concurrent_reload(query, count, state, allowed=None):
        nonlocal changed
        pairs = original(query, count, state, allowed)
        if not changed:
            changed = True
            product(store, 8, [0, 1])
            new = build(store, encoder)
            assert new["generation"] != state.manifest["generation"]
            search.load()
        return pairs

    monkeypatch.setattr(search, "_nearest", concurrent_reload)
    response = search.query([1, 0], limit=1)
    assert response["index"]["generation"] == old["generation"]
    assert response["items"][0]["product"]["id"] == "p00000"
    assert search.manifest["generation"] != old["generation"]


def test_manifest_must_hash_all_loaded_files(tmp_path):
    store, encoder = catalogue(tmp_path, size=1)
    build(store, encoder)
    pointer = store.root / "indexes" / encoder.id / "active.json"
    manifest = json.loads(pointer.read_text())
    manifest["files"].pop("vectors.npy")
    pointer.write_text(canonical(manifest))
    with pytest.raises(ValueError, match="manifest"):
        Search(store, encoder).load()


def test_invalid_single_item_encoder_shape_is_not_silently_accepted(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)

    class Invalid(Encoder):
        def images(self, images):
            return np.ones((len(images) + 1, self.dim), dtype=np.float32)

    encoder = Invalid()
    result = work(store, encoder)
    assert result["completed"] == 0
    with store.connect() as c:
        rows = c.execute("SELECT status,attempts,lease,owner FROM jobs").fetchall()
    assert all(tuple(r) == ("error", 3, None, None) for r in rows)


def test_job_recovery_clears_lease_and_records_rebuild(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    from crumble.jobs import enqueue

    enqueue(store, encoder)
    with store.connect() as c:
        c.execute("UPDATE jobs SET status='running',attempts=3,lease=1,owner='dead'")
    result = work(store, encoder, max_jobs=1)
    assert result["completed"] == 1
    assert result["index_needs_rebuild"]
    with store.connect() as c:
        completed = c.execute("SELECT lease,owner FROM jobs WHERE status='done'").fetchone()
    assert tuple(completed) == (None, None)


def test_removed_images_are_not_processed_and_active_status_is_separate(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    from crumble.jobs import enqueue

    enqueue(store, encoder)
    p = store.product("dress-a")
    with store.connect() as c:
        c.execute("DELETE FROM product_assets WHERE asset_id=?", (p["images"][0],))
    result = work(store, encoder)
    assert result["completed"] == 9
    assert result["failed_attempts"] == 0
    summary = store.summary()
    assert sum(r["count"] for r in summary["active_jobs"]) == 9
    assert sum(r["count"] for r in summary["jobs"]) == 10


def test_reassociation_of_embedded_image_requests_rebuild_without_new_jobs(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    work(store, encoder)
    build(store, encoder)
    assert not needs_build(store, encoder)
    p = store.product("dress-a")
    detached = {**p, "images": []}
    store.save(detached, "detached")
    build(store, encoder)
    store.save(p, "restored")
    result = work(store, encoder)
    assert result["completed"] == 0
    assert result["index_needs_rebuild"]
    build(store, encoder)
    assert not needs_build(store, encoder)


def test_queue_population_has_resumable_source_pages(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    work(store, encoder)
    build(store, encoder)
    search = Search(store, encoder)
    first = populate(store, search, limit=2)
    second = populate(store, search, limit=2, after=first["next_after"])
    assert first["source_products"] == second["source_products"] == 2
    assert first["next_after"] < second["next_after"]
    assert populate(store, search, limit=2, after="zzzz")["next_after"] is None


def test_queue_deduplicates_models_for_same_pair(tmp_path):
    store = Store(tmp_path / "workspace")
    make(store)
    encoder = Encoder()
    work(store, encoder)
    build(store, encoder)
    populate(store, Search(store, encoder), limit=10)
    before = pending(store)["items"]
    with store.connect() as c:
        c.execute(
            "INSERT INTO review_queue SELECT a,b,snapshot_a,snapshot_b,'new-model',score,"
            "'9999' FROM review_queue"
        )
    after = pending(store)["items"]
    assert len(after) == len(before)
    assert all(p["model_id"] == "new-model" for p in after)


def test_category_filter_uses_exact_scoring_even_with_ann(tmp_path):
    from dataclasses import replace

    store, encoder = catalogue(tmp_path, size=2)
    product(store, 5, [0.7, 0.7], category="dress")
    build(store, encoder)
    search = Search(store, encoder)

    class Approximate:
        def search(self, query, count):
            raise AssertionError("Category search must not rely on an unfiltered ANN shortlist")

    search._state = replace(search.load(), ann=Approximate())
    response = search.query([1, 0], category="dress")
    assert response["items"][0]["product"]["id"] == "p00005"
    assert response["approximate"] is False


def test_metadata_only_edit_does_not_require_vector_index_rebuild(tmp_path):
    store, encoder = catalogue(tmp_path, size=1)
    build(store, encoder)
    p = store.product("p00000")
    p["title"] = "Renamed example garment"
    p["category"] = "dress"
    store.save(p, "metadata-changed")
    assert not needs_build(store, encoder)
    response = Search(store, encoder).query([1, 0], category="dress")
    assert response["items"][0]["product"]["title"] == "Renamed example garment"
