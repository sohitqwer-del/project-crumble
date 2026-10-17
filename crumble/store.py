# SPDX-License-Identifier: Apache-2.0
"""One workspace, immutable evidence, explicit transactions and closed handles."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .util import canonical, digest, now

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, width INT, height INT, created TEXT);
CREATE TABLE IF NOT EXISTS products(
 id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, source_hash TEXT NOT NULL,
 title TEXT NOT NULL, brand TEXT NOT NULL, category TEXT NOT NULL, updated TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS products_category ON products(category,id);
CREATE TABLE IF NOT EXISTS snapshots(
 id TEXT PRIMARY KEY, product_id TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS snapshots_product ON snapshots(product_id,created);
CREATE TABLE IF NOT EXISTS product_assets(
 product_id TEXT NOT NULL, asset_id TEXT NOT NULL, ordinal INT NOT NULL,
 PRIMARY KEY(product_id,asset_id));
CREATE INDEX IF NOT EXISTS assets_products ON product_assets(asset_id);
CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY, spec TEXT NOT NULL, dim INT NOT NULL);
CREATE TABLE IF NOT EXISTS vectors(
 asset_id TEXT NOT NULL, model_id TEXT NOT NULL, v BLOB NOT NULL,
 PRIMARY KEY(asset_id,model_id));
CREATE INDEX IF NOT EXISTS vectors_model ON vectors(model_id,asset_id);
CREATE TABLE IF NOT EXISTS jobs(
 asset_id TEXT NOT NULL, model_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 attempts INT NOT NULL DEFAULT 0, lease REAL, owner TEXT, error TEXT, updated TEXT,
 PRIMARY KEY(asset_id,model_id));
CREATE INDEX IF NOT EXISTS pending_jobs ON jobs(model_id,status,updated);
CREATE TABLE IF NOT EXISTS reviews(
 id TEXT PRIMARY KEY, a TEXT NOT NULL, b TEXT NOT NULL, snapshot_a TEXT NOT NULL,
 snapshot_b TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS review_pair ON reviews(a,b,created);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, product_id TEXT, payload TEXT, created TEXT);
"""


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for d in ("assets", "indexes"):
            (self.root / d).mkdir(exist_ok=True)
        with self.connect() as c:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Workspace schema is newer than this release")
            c.executescript(SCHEMA)
            c.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.root / "crumble.sqlite", timeout=30)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA journal_mode=WAL")
            with c:
                yield c
        finally:
            c.close()

    def asset_path(self, asset_id):
        if len(asset_id) != 64 or any(x not in "0123456789abcdef" for x in asset_id):
            raise ValueError("Invalid image identifier")
        return self.root / "assets" / asset_id[:2] / (asset_id + ".jpg")

    def snapshot(self, snapshot_id, c=None):
        if c is None:
            with self.connect() as con:
                return self.snapshot(snapshot_id, con)
        row = c.execute("SELECT payload FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError("Snapshot not found")
        p = json.loads(row[0])
        p["snapshot"] = snapshot_id
        return p

    def product(self, pid, c=None):
        if c is None:
            with self.connect() as con:
                return self.product(pid, con)
        row = c.execute("SELECT snapshot FROM products WHERE id=?", (pid,)).fetchone()
        if row is None:
            raise KeyError("Garment not found")
        return self.snapshot(row[0], c)

    def save(self, payload, source_hash, event=None, expected=None):
        """Source reimports preserve corrections until the source changes."""
        pid, stamp = payload["id"], now()
        payload = {k: v for k, v in payload.items() if k != "snapshot"}
        sid = digest(payload)
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            old = c.execute("SELECT snapshot,source_hash FROM products WHERE id=?", (pid,)).fetchone()
            if expected and (not old or old[0] != expected):
                raise ValueError("This garment changed. Reload before saving.")
            if event is None and old and old[1] == source_hash:
                return old[0], False
            c.execute(
                "INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)", (sid, pid, canonical(payload), stamp)
            )
            c.execute(
                "INSERT INTO products VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "snapshot=excluded.snapshot,source_hash=excluded.source_hash,title=excluded.title,"
                "brand=excluded.brand,category=excluded.category,updated=excluded.updated",
                (pid, sid, source_hash, payload["title"], payload["brand"], payload["category"], stamp),
            )
            previous_assets = {
                r[0] for r in c.execute("SELECT asset_id FROM product_assets WHERE product_id=?", (pid,))
            }
            if previous_assets != set(payload["images"]):
                c.execute(
                    "INSERT INTO meta(key,value) VALUES('catalogue_revision','1') "
                    "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1"
                )
            c.execute("DELETE FROM product_assets WHERE product_id=?", (pid,))
            c.executemany(
                "INSERT INTO product_assets VALUES(?,?,?)",
                [(pid, a, i) for i, a in enumerate(payload["images"])],
            )
            if event:
                c.execute(
                    "INSERT INTO events(product_id,payload,created) VALUES(?,?,?)",
                    (pid, canonical({**event, "before": expected, "after": sid}), stamp),
                )
        return sid, not old or old[0] != sid

    def listing(self, q="", category="", offset=0, limit=30):
        sql, args = "1=1", []
        if q:
            sql += " AND (title LIKE ? ESCAPE '!' OR brand LIKE ? ESCAPE '!')"
            escaped = q.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            args.extend(["%" + escaped + "%"] * 2)
        if category:
            sql += " AND category=?"
            args.append(category)
        with self.connect() as c:
            rows = c.execute(
                "SELECT snapshot FROM products WHERE " + sql + " ORDER BY id LIMIT ? OFFSET ?",
                args + [limit, offset],
            ).fetchall()
            total = c.execute("SELECT count(*) FROM products WHERE " + sql, args).fetchone()[0]
            return {"items": [self.snapshot(r[0], c) for r in rows], "total": total}

    def summary(self):
        with self.connect() as c:
            counts = {
                t: c.execute("SELECT count(*) FROM " + t).fetchone()[0]
                for t in ("products", "assets", "snapshots", "vectors", "reviews")
            }
            counts["jobs"] = [
                dict(r)
                for r in c.execute(
                    "SELECT model_id,status,count(*) AS count FROM jobs GROUP BY model_id,status"
                )
            ]
            counts["active_jobs"] = [
                dict(r)
                for r in c.execute(
                    "SELECT j.model_id,j.status,count(*) AS count FROM jobs j WHERE EXISTS "
                    "(SELECT 1 FROM product_assets p WHERE p.asset_id=j.asset_id) "
                    "GROUP BY j.model_id,j.status"
                )
            ]
            counts["categories"] = [
                dict(r)
                for r in c.execute(
                    "SELECT category,count(*) AS count FROM products GROUP BY category ORDER BY category"
                )
            ]
            return counts
