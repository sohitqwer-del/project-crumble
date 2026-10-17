# SPDX-License-Identifier: Apache-2.0
"""Traceable changes in operation standard minutes, never time guessed from pixels."""

import math

from .normalise import normalise_values
from .structure import FIELD_KEYS
from .util import digest

EMPTY_LIBRARY = {
    "version": "empty/1",
    "scope": "No factory time library configured",
    "illustrative": False,
    "operations": [],
    "rules": [],
}


def validate_library(data):
    if not isinstance(data, dict) or set(data) != {"version", "scope", "illustrative", "operations", "rules"}:
        raise ValueError("Library needs version, scope, illustrative, operations and rules")
    if not all(isinstance(data[k], str) and 0 < len(data[k]) <= 1000 for k in ("version", "scope")):
        raise ValueError("Library version and scope are required")
    if type(data["illustrative"]) is not bool:
        raise ValueError("illustrative must be boolean")
    if not isinstance(data["operations"], list) or len(data["operations"]) > 10000:
        raise ValueError("Invalid operations")
    operations = {}
    for op in data["operations"]:
        if not isinstance(op, dict) or set(op) != {"id", "label", "low", "high", "source", "machine"}:
            raise ValueError("Each operation needs id, label, low, high, source and machine")
        if not all(
            isinstance(op[k], str) and 0 < len(op[k]) <= 1000 for k in ("id", "label", "source", "machine")
        ):
            raise ValueError("Operation descriptions and evidence sources are required")
        for key in ("low", "high"):
            v = op[key]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("Minutes must be finite numbers")
        if not 0 <= op["low"] <= op["high"] <= 1000 or op["id"] in operations:
            raise ValueError("Invalid time range or duplicate operation")
        operations[op["id"]] = op
    if not isinstance(data["rules"], list) or len(data["rules"]) > 10000:
        raise ValueError("Invalid rules")
    seen, owners = set(), {}
    for rule in data["rules"]:
        if (
            not isinstance(rule, dict)
            or set(rule) != {"field", "values", "operations"}
            or not isinstance(rule["field"], str)
            or rule["field"] not in FIELD_KEYS
        ):
            raise ValueError("Invalid rule field")
        if (
            not isinstance(rule["values"], list)
            or not rule["values"]
            or not all(isinstance(v, str) and 0 < len(v) <= 120 for v in rule["values"])
        ):
            raise ValueError("Rules require explicit values; use 'none' for absence")
        key = (rule["field"], tuple(normalise_values(rule["field"], rule["values"])))
        if key in seen:
            raise ValueError("Ambiguous duplicate rule")
        seen.add(key)
        if not isinstance(rule["operations"], list):
            raise ValueError("Rule operations must be a list")
        used = set()
        for item in rule["operations"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"id", "quantity"}
                or not isinstance(item["id"], str)
                or item["id"] not in operations
                or item["id"] in used
            ):
                raise ValueError("Unknown or duplicate operation in rule")
            q = item["quantity"]
            if (
                isinstance(q, bool)
                or not isinstance(q, (int, float))
                or not math.isfinite(q)
                or not 0 < q <= 1000
            ):
                raise ValueError("Operation quantity must be positive and finite")
            used.add(item["id"])
            if item["id"] in owners and owners[item["id"]] != rule["field"]:
                raise ValueError("An operation cannot belong to two fields: this would double-count time")
            owners[item["id"]] = rule["field"]
    return data


def suggest(comparison, library=None):
    data = validate_library(library or EMPTY_LIBRARY)
    operations = {x["id"]: x for x in data["operations"]}
    rules = {
        (r["field"], tuple(normalise_values(r["field"], r["values"]))): r["operations"] for r in data["rules"]
    }
    mapped, unresolved = [], []
    for row in comparison["rows"]:
        if row["status"] not in ("different", "proposal_different"):
            continue
        field = row["key"]
        a = rules.get((field, tuple(normalise_values(field, row["a"]["values"]))))
        b = rules.get((field, tuple(normalise_values(field, row["b"]["values"]))))
        if a is None or b is None:
            unresolved.append(
                {"field": field, "reason": "No operation rule for both before and after values"}
            )
            continue
        qa, qb = ({op["id"]: op["quantity"] for op in ops} for ops in (a, b))
        changes, low, high = [], 0.0, 0.0
        for oid in sorted(qa.keys() | qb.keys()):
            change = qb.get(oid, 0) - qa.get(oid, 0)
            if not change:
                continue
            op = operations[oid]
            lo, hi = sorted((change * op["low"], change * op["high"]))
            low, high = low + lo, high + hi
            changes.append({**op, "quantity_delta": change, "delta_low": lo, "delta_high": hi})
        mapped.append(
            {
                "field": field,
                "before": row["a"]["values"],
                "after": row["b"]["values"],
                "operations": changes,
                "delta_low": round(low, 6),
                "delta_high": round(high, 6),
                "requires_design_review": row["status"].startswith("proposal"),
            }
        )
    low = round(sum(x["delta_low"] for x in mapped), 6) if mapped else None
    high = round(sum(x["delta_high"] for x in mapped), 6) if mapped else None
    return {
        "library_hash": digest(data),
        "library_version": data["version"],
        "scope": data["scope"],
        "illustrative": data["illustrative"],
        "unit": "standard_minutes_per_garment",
        "mapped": mapped,
        "unmapped_changes": unresolved,
        "unknown_fields": comparison["unknown"],
        "mapped_delta": {"low": low, "high": high},
        "new_total_smv": None,
        "status": "review_required" if mapped else "time_data_required",
        "explanation": "This is the change for mapped operations only. It is not a complete garment SMV. "
        "Check quantities, construction, fabric, machines and the time-study basis.",
    }
