# SPDX-License-Identifier: Apache-2.0
"""Atomic, versioned indexes. Exact search streams memory-mapped vector blocks."""

import hashlib
import json
import uuid
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
            "files": {f: file_hash(target / f) for f in names},
        }
        atomic(target / "manifest.json", canonical(manifest).encode())
        atomic(root / "active.json", canonical(manifest).encode())
        return manifest


class Search:
    def __init__(self, store, encoder):
        self.store, self.encoder = store, encoder
        self.manifest = None

    def load(self):
        root = self.store.root / "indexes" / self.encoder.id
        try:
            data = json.loads((root / "active.json").read_text())
        except FileNotFoundError:
            raise ValueError(
                "Index not built for this encoder. Run crumble worker and crumble index."
            ) from None
        if self.manifest and self.manifest["generation"] == data["generation"]:
            return
        generation = data["generation"]
        if len(generation) != 32 or any(c not in "0123456789abcdef" for c in generation):
            raise ValueError("Invalid index generation")
        if data["model_id"] != self.encoder.id or data["dim"] != self.encoder.dim:
            raise ValueError("Index and query encoder do not match")
        folder = root / generation
        for name, expected in data["files"].items():
            if name not in ("vectors.npy", "ids.npy", "hnsw.faiss"):
                raise ValueError("Unexpected index file")
            if file_hash(folder / name) != expected:
                raise ValueError("Index checksum failed; rebuild this generation")
        vectors = np.load(folder / "vectors.npy", mmap_mode="r", allow_pickle=False)
        ids = np.load(folder / "ids.npy", mmap_mode="r", allow_pickle=False)
        if vectors.shape != (data["count"], data["dim"]) or ids.shape != (data["count"],):
            raise ValueError("Invalid index shape")
        self.ann = None
        if data["backend"] == "hnsw":
            import faiss

            faiss.omp_set_num_threads(4)
            self.ann = faiss.read_index(str(folder / "hnsw.faiss"))
        self.vectors, self.ids, self.manifest = vectors, ids, data

    def nearest(self, query, count):
        self.load()
        q = unit(np.asarray(query).reshape(1, -1))
        if q.shape[1] != self.encoder.dim:
            raise ValueError("Query dimension does not match encoder")
        count = min(count, len(self.ids))
        if self.ann is not None:
            _, positions = self.ann.search(q, count)
            ix = positions[0]
            ix = ix[ix >= 0]
            scores = self.vectors[ix] @ q[0]
        else:
            ix, scores = np.empty(0, np.int64), np.empty(0, np.float32)
            for start in range(0, len(self.ids), 32768):
                s = self.vectors[start : start + 32768] @ q[0]
                take = np.argsort(-s, kind="stable")[:count]
                ix = np.concatenate((ix, start + take))
                scores = np.concatenate((scores, s[take]))
                order = np.lexsort((ix, -scores))[:count]
                ix, scores = ix[order], scores[order]
        order = np.lexsort((ix, -scores))
        return [(self.ids[ix[i]].decode(), float(scores[i])) for i in order]

    def query(self, vector, limit=20, category="", exclude="", group=False):
        limit = min(max(1, int(limit)), 100)
        pairs = self.nearest(vector, max(300, limit * 20))
        results, seen, groups = [], set(), set()
        with self.store.connect() as c:
            for aid, score in pairs:
                sql = "SELECT p.id,p.snapshot FROM products p JOIN product_assets a ON p.id=a.product_id WHERE a.asset_id=?"
                args = [aid]
                if category:
                    sql += " AND p.category=?"
                    args.append(category)
                for row in c.execute(sql + " ORDER BY p.id", args).fetchall():
                    if row["id"] == exclude or row["id"] in seen:
                        continue
                    p = self.store.snapshot(row["snapshot"], c)
                    identity = p["identity_group"] or p["id"]
                    if group and identity in groups:
                        continue
                    groups.add(identity)
                    seen.add(p["id"])
                    results.append({"product": p, "score": score, "matched_image": aid})
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
        return {
            "items": results,
            "model": self.encoder.spec,
            "model_id": self.encoder.id,
            "index": self.manifest,
            "score_type": "cosine_similarity_not_probability",
            "candidates_searched": len(pairs),
            "filter_may_limit_results": len(results) < limit and len(pairs) < self.manifest["count"],
        }
