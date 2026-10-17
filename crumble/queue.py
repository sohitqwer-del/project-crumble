# SPDX-License-Identifier: Apache-2.0
import numpy as np

from .util import now

DDL = """CREATE TABLE IF NOT EXISTS review_queue(
 a TEXT,b TEXT,snapshot_a TEXT,snapshot_b TEXT,model_id TEXT,score REAL,created TEXT,
 PRIMARY KEY(a,b,snapshot_a,snapshot_b,model_id))"""


def populate(store, search, limit=100, after=""):
    """Populate one stable source page; next_after resumes a large catalogue."""
    limit = int(limit)
    if not 1 <= limit <= 10000:
        raise ValueError("Queue source limit must be between 1 and 10000")
    with store.connect() as c:
        c.execute(DDL)
        rows = c.execute(
            "SELECT p.id,p.snapshot,a.asset_id,v.v FROM products p JOIN product_assets a ON a.product_id=p.id "
            "JOIN vectors v ON v.asset_id=a.asset_id WHERE a.ordinal=0 AND v.model_id=? "
            "AND p.id>? ORDER BY p.id LIMIT ?",
            (search.encoder.id, after, limit),
        ).fetchall()
    added = 0
    for pid, snapshot, aid, blob in rows:
        p = store.product(pid)
        if p["snapshot"] != snapshot or aid not in p["images"]:
            continue
        neighbours = search.query(
            np.frombuffer(blob, dtype="<f4"),
            3,
            category=p["category"],
            exclude=pid,
        )["items"]
        with store.connect() as c:
            for r in neighbours:
                a, b = sorted((p, r["product"]), key=lambda x: x["id"])
                cursor = c.execute(
                    "INSERT OR IGNORE INTO review_queue VALUES(?,?,?,?,?,?,?)",
                    (a["id"], b["id"], a["snapshot"], b["snapshot"], search.encoder.id, r["score"], now()),
                )
                added += cursor.rowcount
    return {
        "added": added,
        "source_products": len(rows),
        "next_after": rows[-1][0] if len(rows) == limit else None,
    }


def pending(store, limit=50):
    limit = min(max(1, int(limit)), 1000)
    with store.connect() as c:
        c.execute(DDL)
        rows = c.execute(
            """WITH ranked AS (
           SELECT q.*,row_number() OVER (
            PARTITION BY a,b,snapshot_a,snapshot_b ORDER BY created DESC,model_id
           ) AS position FROM review_queue q
          )
          SELECT q.* FROM ranked q
          JOIN products a ON q.a=a.id AND q.snapshot_a=a.snapshot
          JOIN products b ON q.b=b.id AND q.snapshot_b=b.snapshot
          WHERE q.position=1 AND NOT EXISTS(SELECT 1 FROM reviews r WHERE
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
