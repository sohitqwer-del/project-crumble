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
        "no_match_queries": len(rows) - len(present),
        "top1": r1 / len(present) if present else None,
        "top10": r10 / len(present) if present else None,
        "top1_wilson95": wilson(r1, len(present)),
        "confident_claims": len(claims),
        "claim_precision": precision,
        "claim_precision_wilson95": interval,
        "known_match_claim_coverage": coverage,
        "target98_passed": bool(
            present
            and r1 / len(present) >= 0.98
            and precision is not None
            and precision >= 0.98
            and len(claims) >= 100
            and interval[0] >= 0.95
            and coverage >= 0.5
        ),
        "limits": "Intervals are query-level Wilson intervals. Use grouped bootstrap for correlated identities. "
        "Leakage checks cover supplied aliases and hashes only; audit missing aliases independently.",
    }
