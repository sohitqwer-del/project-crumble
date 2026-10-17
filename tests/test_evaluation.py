import pytest

from crumble.evaluation import evaluate


def row(i, positive=True, claimed=True):
    return {
        "query_id": str(i),
        "split": "test",
        "group_ids": ["g" + str(i)],
        "photo_hashes": ["h" + str(i)],
        "positive_ids": ["match"] if positive else [],
        "ranked_ids": ["match"],
        "claimed": claimed,
        "label_source": "synthetic test fixture",
    }


def test_no_match_false_claim_counts_against_precision():
    r = evaluate([row(1), row(2, False)])
    assert r["top1"] == 1
    assert r["claim_precision"] == 0.5
    assert r["target98_passed"] is False
    assert r["no_match_queries"] == 1


def test_alias_and_image_leakage_rejected():
    a, b = row(1), row(2)
    b["split"] = "train"
    b["group_ids"] = a["group_ids"]
    with pytest.raises(ValueError, match="leakage"):
        evaluate([a, b])
    b["group_ids"] = ["new"]
    b["photo_hashes"] = a["photo_hashes"]
    with pytest.raises(ValueError, match="leakage"):
        evaluate([a, b])


def test_no_claims_and_empty_inputs_do_not_pass():
    assert evaluate([row(1, claimed=False)])["claim_precision"] is None
    assert evaluate([])["target98_passed"] is False


def test_declared_threshold_gate_requires_sufficient_support():
    positives = [row(i) for i in range(100)]
    assert evaluate(positives)["target98_passed"] is False
    negatives = []
    for i in range(100, 200):
        negative = row(i, positive=False, claimed=False)
        negative.update(label_independent=True, no_match_verified=True)
        negatives.append(negative)
    assert evaluate(positives + negatives)["target98_passed"] is True
    for negative in negatives:
        negative["group_ids"] = ["one-shared-negative"]
    assert evaluate(positives + negatives)["target98_passed"] is False
    assert evaluate([row(i) for i in range(10)])["target98_passed"] is False
