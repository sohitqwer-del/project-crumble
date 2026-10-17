# SPDX-License-Identifier: Apache-2.0
"""Original drawings: workflow fixtures, not a fashion benchmark."""

import io
from importlib.resources import files

from PIL import Image, ImageDraw

from .ingest import ingest
from .util import atomic


def drawing(kind="dress", colour="#467b8b", sleeve="short", pockets=False, shape="square"):
    im = Image.new("RGB", (600, 750), "#efeee5")
    d, ink = ImageDraw.Draw(im), "#334c49"
    if kind in ("dress", "top"):
        hem = 650 if kind == "dress" else 450
        d.polygon(
            [(220, 130), (260, 115), (340, 115), (380, 130), (405, 300), (440, hem), (160, hem), (195, 300)],
            fill=colour,
            outline=ink,
            width=4,
        )
        if shape == "square":
            d.rectangle((263, 112, 337, 175), fill="#efeee5", outline=ink, width=4)
        else:
            d.polygon([(260, 113), (300, 205), (340, 113)], fill="#efeee5", outline=ink, width=4)
        d.line((260, 114, 340, 114), fill="#efeee5", width=7)
        end = 410 if sleeve == "long" else 235
        d.polygon(
            [(220, 130), (170, 150), (100, end), (166, end + 18), (210, 247)],
            fill=colour,
            outline=ink,
            width=4,
        )
        d.polygon(
            [(380, 130), (430, 150), (500, end), (434, end + 18), (390, 247)],
            fill=colour,
            outline=ink,
            width=4,
        )
        d.line((198, 330, 402, 330), fill=ink, width=3)
        if pockets:
            for x in (208, 334):
                d.rectangle((x, 365, x + 58, 430), fill=colour, outline=ink, width=4)
                d.line((x + 3, 378, x + 55, 378), fill=ink, width=2)
        d.line((170, hem - 15, 430, hem - 15), fill=ink, width=2)
    elif kind == "trousers":
        d.polygon(
            [(190, 130), (410, 130), (445, 655), (320, 655), (300, 330), (280, 655), (155, 655)],
            fill=colour,
            outline=ink,
            width=4,
        )
        d.line((192, 165, 408, 165), fill=ink, width=4)
        d.line((300, 167, 300, 320), fill=ink, width=3)
    else:
        d.polygon([(220, 160), (380, 160), (460, 650), (140, 650)], fill=colour, outline=ink, width=4)
        d.line((217, 185, 383, 185), fill=ink, width=3)
        for x in (230, 265, 300, 335, 370):
            d.line((x, 190, x + (x - 300) * 0.5, 625), fill=ink, width=2)
    d.text((25, 715), "CRUMBLE / ORIGINAL DEMO ILLUSTRATION", fill=ink)
    return im


def make(store):
    if store.summary()["products"]:
        raise ValueError("Demo needs an empty workspace; use a different --workspace")
    specs = [
        (
            "dress-a",
            "Ocean square neck short sleeve midi dress",
            "dress",
            "#467b8b",
            "short",
            False,
            "square",
        ),
        (
            "dress-b",
            "Ocean square neck long sleeve midi dress with patch pockets",
            "dress",
            "#467b8b",
            "long",
            True,
            "square",
        ),
        ("dress-c", "Rust v-neck short sleeve midi dress", "dress", "#b76745", "short", False, "v"),
        ("dress-d", "Moss square neck short sleeve midi dress", "dress", "#74875c", "short", False, "square"),
        ("top-a", "Cream square neck short sleeve top", "top", "#d5cdb1", "short", False, "square"),
        ("top-b", "Navy v-neck long sleeve top", "top", "#3e546c", "long", False, "v"),
        ("trousers-a", "Sand trousers", "trousers", "#b9a680", "short", False, "square"),
        ("trousers-b", "Navy trousers", "trousers", "#40556b", "short", False, "square"),
        ("skirt-a", "Olive pleated skirt", "skirt", "#778569", "short", False, "square"),
        ("skirt-b", "Rust pleated skirt", "skirt", "#af7055", "short", False, "square"),
    ]
    for pid, title, kind, colour, sleeve, pockets, shape in specs:
        buf = io.BytesIO()
        drawing(kind, colour, sleeve, pockets, shape).save(buf, "PNG")
        parts = {}
        if kind in ("dress", "top"):
            parts["pockets"] = {
                "state": "stated",
                "values": ["patch" if pockets else "none"],
                "source": "Original illustration specification; two pockets if present",
            }
        ingest(
            store,
            {
                "id": pid,
                "title": title,
                "brand": "Crumble Atelier",
                "category": kind,
                "rights": "Original programmatic illustration; Apache-2.0",
                "observed_at": "2026-01-01",
                "parts": parts,
            },
            [buf.getvalue()],
        )
    atomic(
        store.root / "operations.json", files("crumble").joinpath("data/demo_operations.json").read_bytes()
    )
    return {"products": len(specs), "data": "synthetic_workflow_demo_not_benchmark"}
