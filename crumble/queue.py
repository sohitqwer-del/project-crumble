# SPDX-License-Identifier: Apache-2.0
import numpy as np

from .util import now

DDL = """CREATE TABLE IF NOT EXISTS review_queue(
 a TEXT,b TEXT,snapshot_a TEXT,snapshot_b TEXT,model_id TEXT,score REAL,created TEXT,
 PRIMARY KEY(a,b,snapshot_a,snapshot_b,model_id))"""


def populate(store, search, limit=100):
    with store.connect() as c:
        c.execute(DDL)
        rows = c.execute(
            "SELECT p.id,v.v FROM products p JOIN product_assets a ON a.product_id=p.id "
            "JOIN vectors v ON v.asset_id=a.asset_id WHERE a.ordinal=0 AND v.model_id=? "
            "ORDER BY p.id LIMIT ?",
            (search.encoder.id, limit),
        ).fetchall()
    added = 0
    for pid, blob in rows:
        p = store.product(pid)
        neighbours = search.query(np.frombuffer(blob, dtype="<f4"), 3, exclude=pid)["items"]
        with store.connect() as c:
            for r in neighbours:
                a, b = sorted((p, r["product"]), key=lambda x: x["id"])
                cursor = c.execute(
                    "INSERT OR IGNORE INTO review_queue VALUES(?,?,?,?,?,?,?)",
                    (a["id"], b["id"], a["snapshot"], b["snapshot"], search.encoder.id, r["score"], now()),
                )
                added += cursor.rowcount
    return {"added": added, "source_products": len(rows)}


def pending(store, limit=50):
    with store.connect() as c:
        c.execute(DDL)
        rows = c.execute(
            """SELECT q.* FROM review_queue q
          JOIN products a ON q.a=a.id AND q.snapshot_a=a.snapshot
          JOIN products b ON q.b=b.id AND q.snapshot_b=b.snapshot
          WHERE NOT EXISTS(SELECT 1 FROM reviews r WHERE
           (r.a=q.a AND r.b=q.b AND r.snapshot_a=q.snapshot_a AND r.snapshot_b=q.snapshot_b)
           OR (r.a=q.b AND r.b=q.a AND r.snapshot_a=q.snapshot_b AND r.snapshot_b=q.snapshot_a))
          ORDER BY q.score DESC,q.a,q.b LIMIT ?""",
            (limit,),
        ).fetchall()
        return {
            "items": [
                {
                    "a": store.snapshot(r["snapshot_a"], c),
                    "b": store.snapshot(r["snapshot_b"], c),
                    "score": r["score"],
                    "model_id": r["model_id"],
                }
                for r in rows
            ]
        }
