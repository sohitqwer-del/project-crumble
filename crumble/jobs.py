# SPDX-License-Identifier: Apache-2.0
"""Resumable embedding jobs with one workspace worker and bounded retries."""

import time
import uuid

from PIL import Image

from .embeddings import unit
from .util import canonical, now, writer_lock


def enqueue(store, encoder, retry=False):
    with store.connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO models VALUES(?,?,?)", (encoder.id, canonical(encoder.spec), encoder.dim)
        )
        c.execute(
            "INSERT OR IGNORE INTO jobs(asset_id,model_id,updated) "
            "SELECT DISTINCT p.asset_id,?,? FROM product_assets p WHERE NOT EXISTS "
            "(SELECT 1 FROM jobs j WHERE j.asset_id=p.asset_id AND j.model_id=?)",
            (encoder.id, now(), encoder.id),
        )
        if retry:
            c.execute(
                "UPDATE jobs SET status='pending',attempts=0,error=NULL,lease=NULL,owner=NULL,updated=? "
                "WHERE model_id=? AND status='error'",
                (now(), encoder.id),
            )


def checked_vectors(encoder, images):
    output = unit(encoder.images(images))
    if output.shape != (len(images), encoder.dim):
        raise ValueError("Encoder returned an unexpected shape")
    return output


def work(store, encoder, batch_size=8, max_jobs=None, retry=False):
    if not 1 <= batch_size <= 64:
        raise ValueError("batch_size must be between 1 and 64")
    if max_jobs is not None and max_jobs < 1:
        raise ValueError("max_jobs must be positive")
    done, failed = 0, 0
    owner = uuid.uuid4().hex
    with writer_lock(store.root / ".worker.lock"):
        enqueue(store, encoder, retry)
        with store.connect() as c:
            # Lock proves no previous worker remains. Interrupted attempts do not consume a retry.
            c.execute(
                "UPDATE jobs SET status='pending',attempts=max(0,attempts-1),lease=NULL,owner=NULL "
                "WHERE status='running' AND model_id=?",
                (encoder.id,),
            )
        while max_jobs is None or done + failed < max_jobs:
            amount = batch_size if max_jobs is None else min(batch_size, max_jobs - done - failed)
            with store.connect() as c:
                rows = c.execute(
                    "SELECT asset_id FROM jobs WHERE model_id=? AND status='pending' "
                    "AND attempts<3 AND EXISTS (SELECT 1 FROM product_assets p WHERE p.asset_id=jobs.asset_id) "
                    "ORDER BY updated,asset_id LIMIT ?",
                    (encoder.id, amount),
                ).fetchall()
                if not rows:
                    break
                ids = [r[0] for r in rows]
                c.executemany(
                    "UPDATE jobs SET status='running',attempts=attempts+1,lease=?,owner=?,updated=? "
                    "WHERE asset_id=? AND model_id=?",
                    [(time.time(), owner, now(), a, encoder.id) for a in ids],
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
                    output = checked_vectors(encoder, list(prepared.values()))
                    vectors.update(zip(prepared, output))
                except Exception:
                    for aid, image in prepared.items():
                        try:
                            vectors[aid] = checked_vectors(encoder, [image])[0]
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
                            "INSERT INTO meta(key,value) VALUES(?, '1') ON CONFLICT(key) "
                            "DO UPDATE SET value=CAST(value AS INTEGER)+1",
                            ("vector_revision:" + encoder.id,),
                        )
                        c.execute(
                            "UPDATE jobs SET status='done',error=NULL,lease=NULL,owner=NULL,updated=? "
                            "WHERE asset_id=? AND model_id=?",
                            (now(), aid, encoder.id),
                        )
                    done += 1
                except Exception as exc:
                    with store.connect() as c:
                        c.execute(
                            "UPDATE jobs SET status=CASE WHEN attempts<3 THEN 'pending' ELSE 'error' END,"
                            "error=?,lease=NULL,owner=NULL,updated=? WHERE asset_id=? AND model_id=?",
                            (type(exc).__name__ + ": " + str(exc)[:500], now(), aid, encoder.id),
                        )
                    failed += 1
    from .retrieval import needs_build

    return {
        "completed": done,
        "failed_attempts": failed,
        "index_needs_rebuild": needs_build(store, encoder),
    }
