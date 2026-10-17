# SPDX-License-Identifier: Apache-2.0
import pytest

from crumble.structure import compare, extract, validate_review


def test_missing_details_are_not_matches():
    r = compare(extract("Dress"), extract("Dress"))
    assert r["same"] == ["category"]
    assert "sleeve_length" in r["unknown"]
    assert r["exact_identity_verified"] is False
    assert r["relationship"] == "unreviewed"


def test_separates_colour_from_construction_changes():
    r = compare(
        extract("Red square neck puff sleeve mini dress"), extract("Blue square neck long sleeve maxi dress")
    )
    assert set(r["different"]) == {"colour", "length"}
    assert "neckline" in r["same"]
    # Puff is a shape, not a length. The unknown length must not be invented.
    assert "sleeve_length" in r["unknown"]
    assert "sleeve_shape" in r["unknown"]


def test_neckline_change_is_explicit():
    r = compare(extract("Black square neck midi dress"), extract("Black halter midi dress"))
    assert r["different"] == ["neckline"]


def test_shirt_dress_is_not_two_garments():
    f = extract("Red shirt-dress")["fields"]["category"]
    assert f["state"] == "stated"
    assert f["values"] == ["dress"]


def test_outfit_title_is_ambiguous():
    f = extract("Shirt and skirt set")["fields"]["category"]
    assert f["state"] == "conflicting"


def test_mini_print_is_not_a_mini_hem():
    f = extract("Mini floral print dress")["fields"]["length"]
    assert f["state"] == "unknown"


def test_negation_not_positive():
    assert extract("Dress without puff sleeves")["fields"]["sleeve_shape"]["state"] == "unknown"


def test_quote_spans_refer_to_original_title():
    title = "RED Square-Neck Long-Sleeve Midi Dress"
    s = extract(title, 123)
    for f in s["fields"].values():
        for e in f["evidence"]:
            assert title[e["span"][0] : e["span"][1]] == e["quote"]
    assert s["fields"]["neckline"]["values"] == ["square"]


def test_unknown_fibre_back_and_seams():
    s = extract("Satin midi dress")
    for key in ("composition", "back", "seams"):
        assert s["fields"][key]["state"] == "unknown"


@pytest.mark.parametrize(
    "data",
    [
        {"a": 1, "b": 1, "relation": "different"},
        {"a": True, "b": 2, "relation": "different"},
        {"a": 1, "b": 2, "relation": "copy"},
        {"a": 1, "b": 2, "relation": "same_visible_design", "changed": ["neckline"]},
        {"a": 1, "b": 2, "relation": "different", "changed": ["arbitrary"]},
        {"a": 1, "b": 2, "relation": "different", "note": "x" * 1001},
        {"a": 1, "b": 2, "relation": ["different"]},
        [],
    ],
)
def test_bad_reviews(data):
    with pytest.raises((ValueError, TypeError)):
        validate_review(data)


def test_review_preserves_uncertainty_and_deduplicates():
    assert validate_review(
        {"a": 1, "b": 2, "relation": "unsure", "changed": ["colour", "colour"], "note": "Back not shown"}
    ) == {"a": 1, "b": 2, "relation": "unsure", "changed": ["colour"], "note": "Back not shown"}


def test_plural_print_names_match():
    r = compare(extract("Polka-dot dress"), extract("Polka dots dress"))
    assert "pattern" in r["same"]


def test_visual_agreement_is_not_a_verified_identity():
    a, b = extract("Dress"), extract("Dress")
    for p in (a, b):
        p["fields"]["neckline"].update(state="inferred", values=["square"])
    r = compare(a, b)
    assert next(x for x in r["rows"] if x["key"] == "neckline")["status"] == "proposal_same"
    assert "neckline" not in r["same"]
    assert "neckline" in r["unknown"]
    assert r["exact_identity_verified"] is False


def test_equivalent_wording_is_not_a_design_difference():
    a, b = extract("Dress"), extract("Dress")
    a["fields"]["neckline"].update(state="verified", values=["Square Neck"])
    b["fields"]["neckline"].update(state="verified", values=["square"])
    a["fields"]["hem"].update(state="inferred", values=["scalloped hem"])
    b["fields"]["hem"].update(state="inferred", values=["scalloped"])
    r = compare(a, b)
    assert "neckline" in r["same"]
    assert next(x for x in r["rows"] if x["key"] == "hem")["status"] == "proposal_same"


def test_fastening_position_is_a_real_difference():
    r = compare(extract("Dress with front zip"), extract("Dress with back zip"))
    assert "closure" in r["different"]
