# SPDX-License-Identifier: Apache-2.0
import json
import uuid

from .models import PartEdit, Review
from .smv import suggest
from .structure import compare
from .util import canonical, digest, now


def comparison(store, a, b, library):
    if a == b:
        raise ValueError("Choose two different garments")
    pa, pb = store.product(a), store.product(b)
    result = compare(pa["structure"], pb["structure"])
    return {
        "a": pa,
        "b": pb,
        "comparison": result,
        "smv": suggest(result, library),
        "reviews": pair_reviews(store, a, b),
    }


def pair_reviews(store, a, b):
    with store.connect() as c:
        rows = c.execute(
            "SELECT id,payload,created FROM reviews WHERE (a=? AND b=?) OR (a=? AND b=?) "
            "ORDER BY created DESC LIMIT 100",
            (a, b, b, a),
        ).fetchall()
        current = {x: store.product(x, c)["snapshot"] for x in (a, b)}
    results = []
    for r in rows:
        data = json.loads(r["payload"])
        stale = current[data["a"]] != data["snapshot_a"] or current[data["b"]] != data["snapshot_b"]
        results.append({"id": r["id"], "created": r["created"], **data, "stale": stale})
    return results


def save_review(store, payload, library):
    data = Review.model_validate(payload).model_dump()
    if data["smv_library_hash"] != digest(library):
        raise ValueError("The operation library changed. Reload the comparison.")
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        a, b = store.product(data["a"], c), store.product(data["b"], c)
        if data["snapshot_a"] != a["snapshot"] or data["snapshot_b"] != b["snapshot"]:
            raise ValueError("A source changed. Reload the comparison before saving.")
        estimate = suggest(compare(a["structure"], b["structure"]), library)
        data["smv_suggestion"] = estimate
        data["time_library"] = library
        rid = uuid.uuid4().hex
        c.execute(
            "INSERT INTO reviews VALUES(?,?,?,?,?,?,?)",
            (rid, data["a"], data["b"], a["snapshot"], b["snapshot"], canonical(data), now()),
        )
    return {"id": rid, "saved": True}


def edit_part(store, pid, payload):
    data = PartEdit.model_validate(payload).model_dump()
    p = store.product(pid)
    claim = data["claim"]
    p["structure"]["fields"][data["field"]].update(
        state=claim["state"],
        values=claim["values"],
        evidence=[{"source": claim["source"], "reviewer": data["reviewer"], "note": data["note"]}],
    )
    with store.connect() as c:
        source_hash = c.execute("SELECT source_hash FROM products WHERE id=?", (pid,)).fetchone()[0]
    sid, changed = store.save(
        p, source_hash, expected=data["snapshot"], event={"kind": "part_review", **data}
    )
    return {"snapshot": sid, "changed": changed}


def history(store, pid):
    with store.connect() as c:
        store.product(pid, c)
        snaps = [
            store.snapshot(r[0], c)
            for r in c.execute(
                "SELECT id FROM snapshots WHERE product_id=? ORDER BY created", (pid,)
            ).fetchall()
        ]
        events = [
            {"created": r["created"], **json.loads(r["payload"])}
            for r in c.execute("SELECT payload,created FROM events WHERE product_id=? ORDER BY id", (pid,))
        ]
        edges = [
            {"created": r["created"], **json.loads(r["payload"])}
            for r in c.execute(
                "SELECT payload,created FROM reviews WHERE a=? OR b=? ORDER BY created", (pid, pid)
            )
        ]
    return {
        "product_id": pid,
        "snapshots": snaps,
        "events": events,
        "reviewed_relationships": edges,
        "date_meaning": "Observed in this workspace; not proof of first design or copying.",
    }
