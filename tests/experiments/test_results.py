import copy

import pytest

from sofa_resp_sim.reporting.experiment_results import summarize_paired_scores


def rows():
    result = []
    # normal, absent, suppressed, worsening: distinct status and algorithm transitions.
    for condition, scores, statuses in [
        (
            "base",
            [0, 0, 0, 2],
            ["observed_scored", "no_qualifying_data", "suppressed_only", "observed_scored"],
        ),
        (
            "variant",
            [1, 0, 2, 1],
            ["observed_scored", "no_qualifying_data", "observed_scored", "observed_scored"],
        ),
    ]:
        for patient, (score, status) in enumerate(zip(scores, statuses, strict=True)):
            result.append(
                {
                    "experiment_run_id": "run",
                    "condition_id": condition,
                    "patient_id": patient,
                    "algorithm_score": score,
                    "score_status": status,
                    "qualifying_pf_count": 0 if patient == 1 else 2,
                    "baseline_score_status": "no_qualifying_data"
                    if patient == 1
                    else "observed_scored",
                    "delta_signed": score - 1,
                    "delta_legacy": max(0, score - 1),
                    "delta_evaluable": None if patient == 1 else score - 1,
                }
            )
    return result


def test_transition_and_denominator_reconciliation():
    result = summarize_paired_scores(rows(), "base")
    for condition in ("base", "variant"):
        for table, size in [("algorithm", 25), ("evidence", 36), ("status", 9)]:
            cells = [
                c
                for c in result["transitions"]
                if c["condition_id"] == condition and c["table"] == table
            ]
            assert len(cells) == size
            assert sum(c["count"] for c in cells) == 4
            assert sorted(p for c in cells for p in c["patient_ids"]) == list(range(4))
            assert all(c["count"] == len(c["patient_ids"]) and c["denominator"] == 4 for c in cells)
    reclass = [r for r in result["reclassification"] if r["condition_id"] == "variant"]
    all_pairs = {r["direction"]: r for r in reclass if r["population"] == "all_patients"}
    evaluable = {
        r["direction"]: r for r in reclass if r["population"] == "both_conditions_evaluable"
    }
    assert [all_pairs[d]["numerator"] for d in ("upward", "downward", "unchanged")] == [2, 1, 1]
    assert all(r["denominator"] == 4 for r in all_pairs.values())
    assert all(r["denominator"] == 3 for r in evaluable.values())
    assert evaluable["unchanged"]["numerator"] == 0
    summary = {r["metric"]: r for r in result["condition_summary"] if r["condition_id"] == "base"}
    assert sum(summary[f"score_eq{s}"]["numerator"] for s in range(5)) == 4
    assert (
        summary["no_qualifying_data"]["numerator"] == summary["suppressed_only"]["numerator"] == 1
    )
    assert summary["qualifying_pf_count"]["estimate"] == 1.5
    assert summary["qualifying_pf_count"]["unit"] == "records"
    assert summary["delta_evaluable_ge1"]["denominator"] == 3
    contrast = next(
        r
        for r in result["paired_contrasts"]
        if r["condition_id"] == "variant" and r["metric"] == "score_ge1"
    )
    assert contrast["n_plus"] == 2 and contrast["n_minus"] == 0
    assert contrast["estimate"] == 0.5
    assert not contrast["structural_identity"]


def test_failed_and_duplicate_pairs_are_not_silently_dropped():
    source = rows()
    for invalid in [source[:-1], source + source[:1]]:
        with pytest.raises(ValueError):
            summarize_paired_scores(invalid, "base")
    invalid = copy.deepcopy(source)
    invalid[0]["experiment_run_id"] = "other"
    with pytest.raises(ValueError):
        summarize_paired_scores(invalid, "base")
