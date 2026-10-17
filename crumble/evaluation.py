# SPDX-License-Identifier: Apache-2.0
"""Evaluate externally judged retrieval runs without inventing confidence labels."""

import math


def wilson(correct, total, z=1.959963984540054):
    if not total:
        return None
    p = correct / total
    d = 1 + z * z / total
    centre = p + z * z / (2 * total)
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return [(centre - radius) / d, (centre + radius) / d]


def evaluate(records, split="test"):
    """Records need group_ids and photo_hashes so declared leakage can be checked."""
    if split not in ("train", "validation", "test"):
        raise ValueError("Invalid evaluation split")
    seen_queries, ownership = set(), {}
    for row in records:
        required = {
            "query_id",
            "split",
            "group_ids",
            "photo_hashes",
            "positive_ids",
            "ranked_ids",
            "claimed",
            "label_source",
        }
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("Incomplete evaluation record")
        if not isinstance(row["query_id"], str) or not row["query_id"]:
            raise ValueError("A nonempty query ID is required")
        if not isinstance(row["label_source"], str) or not row["label_source"].strip():
            raise ValueError("A label evidence reference is required")
        for flag in ("label_independent", "no_match_verified"):
            if flag in row and type(row[flag]) is not bool:
                raise ValueError(flag + " must be boolean")
        if row["query_id"] in seen_queries:
            raise ValueError("Duplicate query")
        seen_queries.add(row["query_id"])
        if row["split"] not in ("train", "validation", "test") or type(row["claimed"]) is not bool:
            raise ValueError("Invalid split or claim")
        if not row["group_ids"] or not row["photo_hashes"] or not row["label_source"]:
            raise ValueError("Group, image and label provenance are required")
        for field in ("group_ids", "photo_hashes", "positive_ids", "ranked_ids"):
            if not isinstance(row[field], list) or not all(isinstance(x, str) and x for x in row[field]):
                raise ValueError("IDs and hashes must be nonempty strings")
            if len(row[field]) != len(set(row[field])):
                raise ValueError("Repeated identifiers in a record")
        for kind in ("group_ids", "photo_hashes"):
            for token in row[kind]:
                key = (kind, token)
                if key in ownership and ownership[key] != row["split"]:
                    raise ValueError("Declared identity or image leakage across splits")
                ownership[key] = row["split"]
    rows = [r for r in records if r["split"] == split]
    present = [r for r in rows if r["positive_ids"]]
    claims = [r for r in rows if r["claimed"]]
    absent = [r for r in rows if not r["positive_ids"]]
    supported_absent = [r for r in absent if r.get("label_independent") and r.get("no_match_verified")]
    # Count connected identity/image components, not repeated photographs of one negative.
    parents = {}

    def find(key):
        parents.setdefault(key, key)
        trail = []
        while parents[key] != key:
            trail.append(key)
            key = parents[key]
        for child in trail:
            parents[child] = key
        return key

    for row in supported_absent:
        keys = [(kind, value) for kind in ("group_ids", "photo_hashes") for value in row[kind]]
        first = find(keys[0])
        for key in keys[1:]:
            parents[find(key)] = first
    negative_components = len({find(key) for key in parents})
    absent_claims = sum(r["claimed"] for r in absent)
    absent_interval = wilson(absent_claims, len(absent))
    negative_support = len(supported_absent) >= 100 and negative_components >= 100
    negative_gate = bool(
        negative_support
        and absent_interval
        and absent_claims / len(absent) <= 0.02
        and absent_interval[1] <= 0.05
    )

    def hit(r, k):
        return bool(set(r["positive_ids"]) & set(r["ranked_ids"][:k]))

    r1 = sum(hit(r, 1) for r in present)
    r10 = sum(hit(r, 10) for r in present)
    correct = sum(hit(r, 1) for r in claims)
    interval = wilson(correct, len(claims))
    covered = sum(r["claimed"] for r in present)
    coverage = covered / len(present) if present else None
    precision = correct / len(claims) if claims else None
    return {
        "split": split,
        "queries": len(rows),
        "known_match_queries": len(present),
        "no_match_queries": len(absent),
        "independently_supported_no_match_queries": len(supported_absent),
        "independent_no_match_components": negative_components,
        "no_match_false_claims": absent_claims,
        "no_match_false_claim_rate": absent_claims / len(absent) if absent else None,
        "no_match_false_claim_wilson95": absent_interval,
        "no_match_support_sufficient": negative_support,
        "evaluation_scope": {
            "known_match_queries": len(present),
            "no_match_queries": len(absent),
            "minimum_supported_no_match_components": 100,
            "negative_labels": "Require declared label_independent=true and no_match_verified=true, with evidence references",
        },
        "top1": r1 / len(present) if present else None,
        "top10": r10 / len(present) if present else None,
        "top1_wilson95": wilson(r1, len(present)),
        "confident_claims": len(claims),
        "claim_precision": precision,
        "claim_precision_wilson95": interval,
        "known_match_claim_coverage": coverage,
        "target98_passed": bool(
            present
            and negative_gate
            and r1 / len(present) >= 0.98
            and precision is not None
            and precision >= 0.98
            and len(claims) >= 100
            and interval[0] >= 0.95
            and coverage >= 0.5
        ),
        "limits": "Intervals are query-level Wilson intervals. Use grouped bootstrap for correlated identities. "
        "Leakage checks cover supplied aliases and hashes only; audit missing aliases independently. "
        "Independent and no-match flags are reviewer declarations; audit their evidence. "
        "Passing this gate does not certify untested brands, galleries or deployment conditions.",
    }
