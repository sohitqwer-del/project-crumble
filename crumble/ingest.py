# SPDX-License-Identifier: Apache-2.0
"""Local imports only. No arbitrary URL fetching or caller-controlled server paths."""

import csv
import hashlib
import io
import json
import warnings
from pathlib import Path

from PIL import Image, ImageOps

from .models import ProductInput
from .structure import extract
from .util import atomic, digest, now

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 20_000_000


def decode(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Image must be nonempty and at most 20 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if im.width * im.height > MAX_PIXELS:
                    raise ValueError("Image must be at most 20 megapixels")
                image = ImageOps.exif_transpose(im).convert("RGB")
                image.load()
        return image
    except (OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or unsafe image") from exc


def asset(store, data):
    image = decode(data)
    image.thumbnail((2048, 2048))
    h = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
    path = store.asset_path(h)
    if not path.exists():
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=95, subsampling=0)
        atomic(path, buf.getvalue())
    with store.connect() as c:
        c.execute("INSERT OR IGNORE INTO assets VALUES(?,?,?,?)", (h, image.width, image.height, now()))
    return h


def ingest(store, metadata, images):
    data = ProductInput.model_validate(metadata).model_dump()
    if not 1 <= len(images) <= 8:
        raise ValueError("Provide 1 to 8 image views per garment")
    ids = list(dict.fromkeys(asset(store, x) for x in images))
    source_hash = digest({"metadata": data, "images": ids})
    structure = extract(data["title"], data["id"])
    for field, claim in data.pop("parts").items():
        structure["fields"][field].update(
            state=claim["state"],
            values=claim["values"],
            evidence=[{"source": claim["source"], "note": claim["note"]}],
        )
    data["structure"] = structure
    data["images"] = ids
    sid, changed = store.save(data, source_hash)
    return {"id": data["id"], "snapshot": sid, "changed": changed}


def import_file(store, manifest, image_root, report=None):
    """Stream JSONL/CSV. Images stay inside a caller-selected import root."""
    root, path = Path(image_root).resolve(), Path(manifest)
    counts = {"ok": 0, "unchanged": 0, "error": 0}
    output = Path(report).open("w") if report else None
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = csv.DictReader(f) if path.suffix.lower() == ".csv" else iter(f)
            for number, raw in enumerate(rows, 1):
                try:
                    row = json.loads(raw) if isinstance(raw, str) else dict(raw)
                    names = row.pop("images", row.pop("image_path", None))
                    if isinstance(names, str):
                        names = json.loads(names) if names.lstrip().startswith("[") else [names]
                    if not isinstance(names, list) or not 1 <= len(names) <= 8:
                        raise ValueError("images must contain 1 to 8 relative filenames")
                    parts = row.get("parts")
                    if isinstance(parts, str):
                        row["parts"] = json.loads(parts) if parts else {}
                    images = []
                    for name in names:
                        target = (root / name).resolve()
                        if not target.is_relative_to(root) or not target.is_file():
                            raise ValueError("Image path must be a file inside --image-root")
                        if target.stat().st_size > MAX_BYTES:
                            raise ValueError("Image exceeds 20 MB")
                        images.append(target.read_bytes())
                    result = ingest(store, row, images)
                    counts["ok" if result["changed"] else "unchanged"] += 1
                    record = {"line": number, "ok": True, **result}
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    counts["error"] += 1
                    record = {"line": number, "ok": False, "error": str(exc)[:1000]}
                if output:
                    output.write(json.dumps(record) + "\n")
    finally:
        if output:
            output.close()
    return counts
