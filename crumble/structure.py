# SPDX-License-Identifier: Apache-2.0
"""Evidence-backed garment descriptions. Title rules are a baseline, not vision."""
import re
from .normalise import normalise_values

VERSION = "crumble-structure/1"
EXTRACTOR = "title-rules/0.1"
# Parts and global attributes are separate; matching a collar is not matching a dress.
FIELDS = [
    ("category", "Garment type", "identity"),
    ("silhouette", "Overall shape", "structure"),
    ("neckline", "Neckline", "structure"),
    ("sleeve_length", "Sleeve length", "structure"),
    ("sleeve_shape", "Sleeve shape", "structure"),
    ("length", "Garment length", "structure"),
    ("waist", "Waist position", "structure"),
    ("hem", "Hem detail", "structure"),
    ("closure", "Fastening", "structure"),
    ("pockets", "Pocket detail", "structure"),
    ("fabric", "Fabric description", "surface"),
    ("pattern", "Print or pattern", "surface"),
    ("colour", "Colour", "surface"),
    ("detail", "Other detail", "surface"),
    ("back", "Back construction", "construction"),
    ("seams", "Seam construction", "construction"),
    ("composition", "Fibre composition", "construction"),
]
RULES = {
    "category": {
        "dress": r"\b(?:shirt[ -]dress|dresses|dress|gown)\b",
        "top": r"\b(?:top|blouse|t[ -]?shirt|tee|camisole|cami|shirt)\b",
        "skirt": r"\bskirt\b", "trousers": r"\b(?:trousers|pants|jeans|leggings)\b",
        "shorts": r"\bshorts\b", "jumpsuit": r"\b(?:jumpsuit|playsuit|romper)\b",
        "knitwear": r"\b(?:cardigan|sweater|jumper|pullover)\b",
        "outerwear": r"\b(?:jacket|coat|blazer|parka|gilet)\b",
    },
    "silhouette": {"a-line": r"\ba[ -]line\b", "bodycon": r"\bbodycon\b",
                   "shift": r"\bshift\b", "oversized": r"\boversized\b",
                   "fit and flare": r"\bfit[ -]and[ -]flare\b"},
    "neckline": {"square": r"\bsquare[ -]neck(?:line)?\b", "v-neck": r"\bv[ -]neck\b",
                 "halter": r"\bhalter(?:neck)?\b", "crew": r"\bcrew[ -]neck\b",
                 "scoop": r"\bscoop[ -]neck\b", "sweetheart": r"\bsweetheart\b",
                 "off shoulder": r"\boff[ -](?:the[ -])?shoulder\b",
                 "one shoulder": r"\bone[ -]shoulder\b"},
    "sleeve_length": {"sleeveless": r"\bsleeveless\b", "long": r"\blong[ -]sleeve[sd]?\b",
                      "short": r"\bshort[ -]sleeve[sd]?\b", "three quarter": r"\b(?:3/4|three[ -]quarter)[ -]sleeve[sd]?\b"},
    "sleeve_shape": {"puff": r"\bpuff(?:ed)?[ -]sleeve[sd]?\b",
                     "balloon": r"\bballoon[ -]sleeve[sd]?\b",
                     "bell": r"\bbell[ -]sleeve[sd]?\b",
                     "cap": r"\bcap[ -]sleeve[sd]?\b"},
    "length": {"mini": r"\bmini\b", "midi": r"\bmidi\b", "maxi": r"\bmaxi\b",
               "cropped": r"\b(?:cropped|crop[ -]top)\b"},
    "waist": {"high": r"\bhigh[ -]waist(?:ed)?\b", "low": r"\blow[ -]waist(?:ed)?\b",
              "dropped": r"\bdrop(?:ped)?[ -]waist\b", "empire": r"\bempire[ -](?:line|waist)\b"},
    "hem": {"asymmetric": r"\basymmetric(?:al)?[ -]hem\b",
            "scalloped": r"\bscalloped[ -]hem\b", "split": r"\b(?:side[ -])?split[ -]hem\b"},
    "closure": {"button front": r"\bbutton[ -](?:front|through|down)(?![ -]collar)\b",
                "zip front": r"\b(?:zip(?:per)?[ -]front|front[ -]zip(?:per)?)\b",
                "zip back": r"\b(?:zip(?:per)?[ -]back|back[ -]zip(?:per)?)\b",
                "zip side": r"\b(?:zip(?:per)?[ -]side|side[ -]zip(?:per)?)\b",
                "zip": r"\bzip[ -]up\b"},
    "pockets": {"cargo": r"\bcargo[ -]pockets?\b", "patch": r"\bpatch[ -]pockets?\b"},
    "fabric": {x: r"\b" + x + r"\b" for x in ("satin", "denim", "ribbed", "chiffon", "velvet", "lace", "cable knit")},
    "pattern": {"floral": r"\bfloral\b", "leopard": r"\bleopard\b", "striped": r"\bstrip(?:ed|es)\b",
                "gingham": r"\bgingham\b", "polka dot": r"\bpolka[ -]dots?\b", "plain": r"\bplain\b"},
    "colour": {x: r"\b" + x + r"\b" for x in ("black", "white", "red", "blue", "green", "pink", "cream", "brown", "navy", "yellow", "purple", "orange", "beige")},
    "detail": {"ruched": r"\bruched\b", "cutout": r"\bcut[ -]?out\b",
               "bow": r"\bbow[ -](?:detail|front|back)\b", "ruffle": r"\bruffl(?:e|ed)\b"},
}
MULTI = {"colour", "fabric", "pattern", "detail"}
RELATIONS = {
    "same_visible_design": "Same visible design",
    "modified_design": "Changed design",
    "shared_detail": "Shared detail only",
    "different": "Different garments",
    "unsure": "Not enough evidence",
}
FIELD_KEYS = {f[0] for f in FIELDS}

def extract(title, product_id=None):
    title = str(title or "")
    fields = {}
    for key, label, group in FIELDS:
        hits = []
        for value, pattern in RULES.get(key, {}).items():
            for m in re.finditer(pattern, title, re.I):
                prefix = title[max(0, m.start() - 30):m.start()]
                if re.search(r"\b(?:no|not|without|non)[ -]+(?:\w+[ -]+){0,2}$", prefix, re.I):
                    continue
                hits.append({"value": value, "source": "title", "quote": m.group(),
                             "span": [m.start(), m.end()]})
        if key == "category":
            # A shirt dress is one garment. Co-ords and outfit titles stay ambiguous.
            hits = [h for h in hits if not any(o["span"][0] <= h["span"][0] and
                    o["span"][1] > h["span"][1] for o in hits)]
        values = sorted({h["value"] for h in hits})
        state = "stated" if values else "unknown"
        if len(values) > 1 and key not in MULTI:
            state = "conflicting"
        fields[key] = {"label": label, "group": group, "state": state,
                       "values": values, "evidence": hits}
    # A mini floral print describes the motif, not the hem.
    for key in ("length",):
        f = fields[key]
        if any(re.search(r"^\s+(?:floral|flower|print|pattern|dot)", title[h["span"][1]:], re.I)
               for h in f["evidence"]):
            f.update(state="unknown", values=[], evidence=[])
    return {"schema_version": VERSION, "extractor": EXTRACTOR, "product_id": product_id,
            "source_title": title, "fields": fields}

def compare(a, b):
    """Compare statements only. Missing values never count as agreements."""
    rows = []
    for key, label, group in FIELDS:
        x, y = a["fields"][key], b["fields"][key]
        status = "unknown"
        if x["state"] == "conflicting" or y["state"] == "conflicting":
            status = "conflicting"
        elif x["state"] in ("stated", "verified", "inferred") and y["state"] in ("stated", "verified", "inferred"):
            status = "same" if normalise_values(key,x["values"]) == normalise_values(key,y["values"]) else "different"
            if "inferred" in (x["state"],y["state"]):
                status = "proposal_" + status
        rows.append({"key": key, "label": label, "group": group, "status": status, "a": x, "b": y})
    return {"schema_version": VERSION, "rows": rows,
            "same": [r["key"] for r in rows if r["status"] == "same"],
            "different": [r["key"] for r in rows if r["status"] == "different"],
            "unknown": [r["key"] for r in rows if r["status"] in ("unknown", "conflicting", "proposal_same", "proposal_different")],
            "relationship": "unreviewed", "exact_identity_verified": False}

def validate_review(data):
    if not isinstance(data, dict):
        raise ValueError("Review must be an object")
    a, b = data.get("a"), data.get("b")
    if any(type(v) is not int or v <= 0 or v > 10**12 for v in (a, b)) or a == b:
        raise ValueError("Choose two different catalogue products")
    if data.get("relation") not in RELATIONS:
        raise ValueError("Choose a relationship")
    changed = data.get("changed", [])
    if not isinstance(changed, list) or any(not isinstance(x, str) or x not in FIELD_KEYS for x in changed):
        raise ValueError("Invalid changed parts")
    if data["relation"] == "same_visible_design" and changed:
        raise ValueError("A same-design label cannot also have changed parts")
    note = data.get("note", "")
    if not isinstance(note, str) or len(note) > 1000:
        raise ValueError("Note must be at most 1,000 characters")
    return {"a": a, "b": b, "relation": data["relation"],
            "changed": sorted(set(changed)), "note": note}

