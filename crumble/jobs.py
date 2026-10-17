# SPDX-License-Identifier: Apache-2.0
"""Resumable embedding jobs with one workspace worker and bounded retries."""

import time

from PIL import Image

from .embeddings import unit
from .util import canonical, now, writer_lock


def enqueue(store, encoder, retry=False):
    with store.connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO models VALUES(?,?,?)", (encoder.id, canonical(encoder.spec), encoder.dim)
        )
        c.execute(
            """INSERT OR IGNORE INTO jobs(asset_id,model_id,updated)
                     SELECT DISTINCT asset_id,?,? FROM product_assets""",
            (encoder.id, now()),
        )
        if retry:
            c.execute(
                "UPDATE jobs SET status='pending',attempts=0,error=NULL WHERE model_id=? AND status='error'",
                (encoder.id,),
            )


def work(store, encoder, batch_size=8, max_jobs=None, retry=False):
    if not 1 <= batch_size <= 64:
        raise ValueError("batch_size must be between 1 and 64")
    if max_jobs is not None and max_jobs < 1:
        raise ValueError("max_jobs must be positive")
    done, failed = 0, 0
    with writer_lock(store.root / ".worker.lock"):
        enqueue(store, encoder, retry)
        with store.connect() as c:
            # Lock proves no previous worker remains. Interrupted attempts do not consume a retry.
            c.execute(
                "UPDATE jobs SET status='pending',attempts=max(0,attempts-1) "
                "WHERE status='running' AND model_id=?",
                (encoder.id,),
            )
        while max_jobs is None or done + failed < max_jobs:
            amount = batch_size if max_jobs is None else min(batch_size, max_jobs - done - failed)
            with store.connect() as c:
                rows = c.execute(
                    "SELECT asset_id FROM jobs WHERE model_id=? AND status='pending' "
                    "AND attempts<3 ORDER BY updated,asset_id LIMIT ?",
                    (encoder.id, amount),
                ).fetchall()
                if not rows:
                    break
                ids = [r[0] for r in rows]
                c.executemany(
                    "UPDATE jobs SET status='running',attempts=attempts+1,lease=?,updated=? "
                    "WHERE asset_id=? AND model_id=?",
                    [(time.time(), now(), a, encoder.id) for a in ids],
                )
            prepared, errors, vectors = {}, {}, {}
            for aid in ids:
                try:
                    with Image.open(store.asset_path(aid)) as im:
                        prepared[aid] = im.convert("RGB")
                except Exception as exc:
                    errors[aid] = exc
            if prepared:
                try:
                    output = unit(encoder.images(list(prepared.values())))
                    if output.shape != (len(prepared), encoder.dim):
                        raise ValueError("Encoder returned an unexpected shape")
                    vectors.update(zip(prepared, output))
                except Exception:
                    for aid, image in prepared.items():
                        try:
                            vectors[aid] = unit(encoder.images([image]))[0]
                        except Exception as exc:
                            errors[aid] = exc
                finally:
                    for image in prepared.values():
                        image.close()
            for aid in ids:
                try:
                    if aid in errors:
                        raise errors[aid]
                    v = vectors[aid]
                    if len(v) != encoder.dim:
                        raise ValueError("Encoder dimension changed")
                    with store.connect() as c:
                        c.execute(
                            "INSERT OR REPLACE INTO vectors VALUES(?,?,?)",
                            (aid, encoder.id, v.astype("<f4").tobytes()),
                        )
                        c.execute(
                            "UPDATE jobs SET status='done',error=NULL,updated=? "
                            "WHERE asset_id=? AND model_id=?",
                            (now(), aid, encoder.id),
                        )
                    done += 1
                except Exception as exc:
                    with store.connect() as c:
                        c.execute(
                            "UPDATE jobs SET status=CASE WHEN attempts<3 THEN 'pending' ELSE 'error' END,"
                            "error=?,updated=? WHERE asset_id=? AND model_id=?",
                            (type(exc).__name__ + ": " + str(exc)[:500], now(), aid, encoder.id),
                        )
                    failed += 1
    return {"completed": done, "failed_attempts": failed}
