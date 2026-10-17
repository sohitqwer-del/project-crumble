import copy
import json
from importlib.resources import files

import pytest

from crumble.smv import suggest, validate_library
from crumble.structure import compare, extract


def example():
    return json.loads(files("crumble").joinpath("data/demo_operations.json").read_text())


def test_reverse_delta_and_unknown_values():
    a, b = extract("Short sleeve top"), extract("Long sleeve top")
    lib = example()
    forward = suggest(compare(a, b), lib)
    reverse = suggest(compare(b, a), lib)
    assert forward["mapped_delta"] == {"low": 0.9, "high": 1.7}
    assert reverse["mapped_delta"] == {"low": -1.7, "high": -0.9}
    assert suggest(compare(extract("Top"), b), lib)["mapped_delta"]["low"] is None
    assert suggest(compare(a, b))["mapped_delta"]["low"] is None


def test_unmapped_changes_never_imply_zero():
    s = suggest(compare(extract("Square neck top"), extract("V-neck top")), example())
    assert s["mapped_delta"] == {"low": None, "high": None}
    assert len(s["unmapped_changes"]) == 1
    assert s["new_total_smv"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, True, "0.4"])
def test_invalid_time_values(bad):
    lib = example()
    lib["operations"][0]["low"] = bad
    with pytest.raises(ValueError):
        validate_library(lib)


def test_duplicate_and_overlapping_operations_rejected():
    lib = example()
    lib["rules"].append(copy.deepcopy(lib["rules"][0]))
    with pytest.raises(ValueError):
        validate_library(lib)
    lib = example()
    r = copy.deepcopy(lib["rules"][0])
    r["field"] = "hem"
    lib["rules"].append(r)
    with pytest.raises(ValueError, match="double-count"):
        validate_library(lib)


def test_unchanged_operation_cancels():
    lib = example()
    lib["rules"][1]["operations"] = [{"id": "hem-short", "quantity": 2}]
    d = suggest(compare(extract("Short sleeve top"), extract("Long sleeve top")), lib)
    assert d["mapped_delta"] == {"low": 0, "high": 0}
    assert d["mapped"][0]["operations"] == []


def test_visual_proposals_are_not_verified():
    a, b = extract("Short sleeve top"), extract("Long sleeve top")
    b["fields"]["sleeve_length"]["state"] = "inferred"
    result = suggest(compare(a, b), example())
    assert result["mapped"][0]["requires_design_review"] is True
    assert result["status"] == "review_required"
