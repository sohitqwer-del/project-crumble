# SPDX-License-Identifier: Apache-2.0
"""Atomic, versioned indexes. Exact search streams memory-mapped vector blocks."""

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .embeddings import unit
from .util import atomic, canonical, now, writer_lock


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_revisions(connection, model_id):
    keys = ("catalogue_revision", "vector_revision:" + model_id)
    values = dict(connection.execute("SELECT key,value FROM meta WHERE key IN (?,?)", keys))
    return {key: int(values.get(key, 0)) for key in keys}


def needs_build(store, encoder):
    """Detect source changes even when all currently associated images were embedded before."""
    with store.connect() as c:
        c.execute("BEGIN")
        if not c.execute(
            "SELECT 1 FROM vectors v WHERE v.model_id=? AND EXISTS "
            "(SELECT 1 FROM product_assets p WHERE p.asset_id=v.asset_id) LIMIT 1",
            (encoder.id,),
        ).fetchone():
            return False
        revisions = source_revisions(c, encoder.id)
    active = store.root / "indexes" / encoder.id / "active.json"
    try:
        manifest = json.loads(active.read_text(encoding="utf-8"))
        return manifest.get("source_revisions") != revisions
    except (OSError, ValueError):
        return True


def build(store, encoder, backend="exact"):
    if backend not in ("exact", "hnsw"):
        raise ValueError("Index backend must be exact or hnsw")
    root = store.root / "indexes" / encoder.id
    root.mkdir(exist_ok=True)
    with writer_lock(root / ".build.lock"):
        generation = uuid.uuid4().hex
        target = root / generation
        target.mkdir()
        sql = (
            "SELECT v.asset_id,v.v FROM vectors v WHERE v.model_id=? AND EXISTS "
            "(SELECT 1 FROM product_assets p WHERE p.asset_id=v.asset_id) ORDER BY v.asset_id"
        )
        with store.connect() as c:
            c.execute("BEGIN")
            revisions = source_revisions(c, encoder.id)
            n = c.execute("SELECT count(*) FROM (" + sql + ")", (encoder.id,)).fetchone()[0]
            if n == 0:
                raise ValueError("No vectors. Run crumble worker first; previous index was preserved.")
            vectors = np.lib.format.open_memmap(
                target / "vectors.npy", mode="w+", dtype="<f4", shape=(n, encoder.dim)
            )
            ids = np.lib.format.open_memmap(target / "ids.npy", mode="w+", dtype="S64", shape=(n,))
            cursor, start = c.execute(sql, (encoder.id,)), 0
            while rows := cursor.fetchmany(4096):
                block = np.frombuffer(b"".join(r[1] for r in rows), dtype="<f4").reshape(-1, encoder.dim)
                vectors[start : start + len(rows)] = unit(block)
                ids[start : start + len(rows)] = [r[0].encode() for r in rows]
                start += len(rows)
            if start != n:
                raise ValueError("Vector count changed during index build")
            vectors.flush()
            ids.flush()
        names = ["vectors.npy", "ids.npy"]
        if backend == "hnsw":
            import faiss

            faiss.omp_set_num_threads(4)
            index = faiss.IndexHNSWFlat(encoder.dim, 32, faiss.METRIC_INNER_PRODUCT)
            index.hnsw.efConstruction = 160
            index.hnsw.efSearch = 128
            for start in range(0, n, 4096):
                index.add(np.asarray(vectors[start : start + 4096]))
            faiss.write_index(index, str(target / "hnsw.faiss"))
            names.append("hnsw.faiss")
        manifest = {
            "schema": 1,
            "generation": generation,
            "model_id": encoder.id,
            "model": encoder.spec,
            "dim": encoder.dim,
            "count": n,
            "backend": backend,
            "created": now(),
            "source_revisions": revisions,
            "files": {f: file_hash(target / f) for f in names},
        }
        atomic(target / "manifest.json", canonical(manifest).encode())
        atomic(root / "active.json", canonical(manifest).encode())
        return manifest


@dataclass(frozen=True)
class IndexState:
    vectors: object
    ids: object
    manifest: dict
    ann: object = None


def top_positions(scores, positions, count):
    """Bounded top-k with deterministic position ordering for tied scores."""
    if len(scores) > count:
        threshold = np.partition(scores, len(scores) - count)[len(scores) - count]
        better = np.flatnonzero(scores > threshold)
        tied = np.flatnonzero(scores == threshold)
        tied = tied[np.argsort(positions[tied], kind="stable")[: count - len(better)]]
        selected = np.concatenate((better, tied))
    else:
        selected = np.arange(len(scores))
    return selected[np.lexsort((positions[selected], -scores[selected]))]


class Search:
    def __init__(self, store, encoder):
        self.store, self.encoder = store, encoder
        self.manifest = None
        self._state = None
        self._load_lock = threading.RLock()

    def load(self):
        # Readers keep one immutable generation while another thread reloads.
        with self._load_lock:
            return self._load()

    def _load(self):
        root = self.store.root / "indexes" / self.encoder.id
        try:
            data = json.loads((root / "active.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(
                "Index not built for this encoder. Run crumble worker and crumble index."
            ) from None
        if self._state and self._state.manifest["generation"] == data["generation"]:
            return self._state
        generation = data["generation"]
        if len(generation) != 32 or any(c not in "0123456789abcdef" for c in generation):
            raise ValueError("Invalid index generation")
        if data["model_id"] != self.encoder.id or data["dim"] != self.encoder.dim:
            raise ValueError("Index and query encoder do not match")
        backend = data.get("backend")
        required = {"vectors.npy", "ids.npy"}
        if backend == "hnsw":
            required.add("hnsw.faiss")
        elif backend != "exact":
            raise ValueError("Invalid index backend")
        if set(data.get("files", {})) != required:
            raise ValueError("Invalid index file manifest")
        folder = root / generation
        for name, expected in data["files"].items():
            if file_hash(folder / name) != expected:
                raise ValueError("Index checksum failed; rebuild this generation")
        vectors = np.load(folder / "vectors.npy", mmap_mode="r", allow_pickle=False)
        ids = np.load(folder / "ids.npy", mmap_mode="r", allow_pickle=False)
        if (
            vectors.shape != (data["count"], data["dim"])
            or ids.shape != (data["count"],)
            or vectors.dtype != np.dtype("<f4")
            or ids.dtype != np.dtype("S64")
        ):
            raise ValueError("Invalid index shape or dtype")
        ann = None
        if backend == "hnsw":
            import faiss

            faiss.omp_set_num_threads(4)
            ann = faiss.read_index(str(folder / "hnsw.faiss"))
            if ann.ntotal != data["count"] or ann.d != data["dim"]:
                raise ValueError("ANN index does not match vector generation")
        state = IndexState(vectors, ids, data, ann)
        self.vectors, self.ids, self.ann, self.manifest = vectors, ids, ann, data
        self._state = state
        return state

    def _nearest(self, query, count, state, allowed=None):
        q = unit(np.asarray(query).reshape(1, -1))
        if q.shape[1] != self.encoder.dim:
            raise ValueError("Query dimension does not match encoder")
        count = min(max(0, int(count)), len(state.ids))
        if count == 0:
            return []
        if state.ann is not None and allowed is None:
            _, positions = state.ann.search(q, count)
            ix = positions[0]
            ix = ix[ix >= 0]
            scores = state.vectors[ix] @ q[0]
        else:
            ix, scores = np.empty(0, np.int64), np.empty(0, np.float32)
            for start in range(0, len(state.ids), 32768):
                positions = np.arange(start, min(start + 32768, len(state.ids)))
                if allowed is not None:
                    mask = np.fromiter(
                        (aid in allowed for aid in state.ids[start : start + 32768]),
                        dtype=bool,
                        count=len(positions),
                    )
                    positions = positions[mask]
                if not len(positions):
                    continue
                block = state.vectors[start : start + 32768] if allowed is None else state.vectors[positions]
                values = block @ q[0]
                selected = top_positions(values, positions, count)
                ix = np.concatenate((ix, positions[selected]))
                scores = np.concatenate((scores, values[selected]))
                selected = top_positions(scores, ix, count)
                ix, scores = ix[selected], scores[selected]
        order = np.lexsort((ix, -scores))
        return [(state.ids[ix[i]].decode(), float(scores[i])) for i in order]

    def nearest(self, query, count):
        return self._nearest(query, count, self.load())

    def _hydrate(self, c, pairs, category, exclude, limit, group):
        by_asset = {}
        for start in range(0, len(pairs), 400):
            batch = [aid for aid, _ in pairs[start : start + 400]]
            sql = (
                "SELECT a.asset_id,p.id,s.payload,p.snapshot FROM product_assets a "
                "JOIN products p ON p.id=a.product_id JOIN snapshots s ON s.id=p.snapshot "
                "WHERE a.asset_id IN (" + ",".join("?" for _ in batch) + ") AND p.id!=?"
            )
            args = batch + [exclude]
            if category:
                sql += " AND p.category=?"
                args.append(category)
            for row in c.execute(sql + " ORDER BY p.id", args):
                by_asset.setdefault(row["asset_id"], []).append(row)
        results, seen, groups = [], set(), set()
        for aid, score in pairs:
            for row in by_asset.get(aid, ()):
                if row["id"] in seen:
                    continue
                p = json.loads(row["payload"])
                p["snapshot"] = row["snapshot"]
                identity = p.get("identity_group") or p["id"]
                if group and identity in groups:
                    continue
                seen.add(p["id"])
                groups.add(identity)
                results.append({"product": p, "score": score, "matched_image": aid})
                if len(results) == limit:
                    return results
        return results

    def query(self, vector, limit=20, category="", exclude="", group=False):
        limit = min(max(1, int(limit)), 100)
        state = self.load()
        with self.store.connect() as c:
            c.execute("BEGIN")
            allowed = None
            if category:
                allowed = {
                    r[0].encode()
                    for r in c.execute(
                        "SELECT DISTINCT a.asset_id FROM product_assets a JOIN products p "
                        "ON p.id=a.product_id WHERE p.category=? AND p.id!=?",
                        (category, exclude),
                    )
                }
            available = len(state.ids) if allowed is None else min(len(state.ids), len(allowed))
            count = min(max(300, limit * 20), available)
            # Expand when multiple views, grouped identities or replaced assets crowd a shortlist.
            while True:
                pairs = self._nearest(vector, count, state, allowed)
                results = self._hydrate(c, pairs, category, exclude, limit, group)
                if len(results) >= limit or len(pairs) < count or count >= available:
                    break
                count = min(available, count * 2)
        return {
            "items": results,
            "model": self.encoder.spec,
            "model_id": self.encoder.id,
            "index": state.manifest,
            "score_type": "cosine_similarity_not_probability",
            "candidates_searched": len(pairs),
            "search_backend": "exact_filtered" if allowed is not None else state.manifest["backend"],
            "approximate": allowed is None and state.ann is not None,
            "filter_may_limit_results": False,
        }
