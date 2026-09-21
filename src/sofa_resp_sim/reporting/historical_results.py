"""V3 eligibility and observation-opportunity estimands over paired score rows."""

from __future__ import annotations

from collections import Counter

from .experiment_results import METRICS, summarize_paired_scores

C_STRATA = ("0", "1", "ge2")
STATES = ("eligible", "ineligible", "indeterminate")


def eligibility(acute, baseline, evaluable, c):
    if c not in C_STRATA or not isinstance(c, str):
        raise ValueError("C must be one of 0, 1, ge2")
    for value in (acute, baseline):
        if type(value) is not int or value not in range(5):
            raise ValueError("Respiratory algorithm scores must be integers 0..4")
    contribution = 2 if c == "ge2" else int(c)
    algorithm = contribution + max(acute - baseline, 0) >= 2
    state = (
        "eligible"
        if c == "ge2"
        else ("eligible" if algorithm else "ineligible")
        if evaluable
        else "indeterminate"
    )
    return algorithm, state


def score_diagnostics(result):
    events = result["events"]
    acute = [e for e in events if e["in_acute_target"]]
    baseline = [e for e in events if e["in_baseline_window"]]
    selected = next((e for e in baseline if e["selected_baseline"]), None)
    day = [e for e in baseline if selected is not None and e["bin_epoch"] == selected["bin_epoch"]]
    recorded = [e for e in acute if e.get("pao2_meas") is not None or e.get("spo2_obs") is not None]
    converted = [e for e in recorded if e["pao2_used_mmhg"] is not None]
    linked = [e for e in converted if e["fio2_fraction"] is not None]
    eligible = [e for e in acute if e["qualifies_acute"]]
    contexts = {e["event_id"]: e for e in result["context_events"]}
    for event in events:
        source = contexts.get(event["fio2_source_event_id"], {})
        origin = source.get("value_origin_minute", source.get("measurement_minute"))
        event["fio2_value_age_minutes"] = (
            event["measurement_minute"] - origin if origin is not None else None
        )
        truth = event.get("synthetic_delivered_fio2_fraction")
        event["synthetic_fio2_error_fraction"] = (
            event["fio2_fraction"] - truth
            if truth is not None and event["fio2_fraction"] is not None
            else None
        )

    def mean(key):
        values = [e[key] for e in acute if e.get(key) is not None]
        return sum(values) / len(values) if values else None

    return {
        "mean_fio2_source_age_minutes": mean("fio2_source_age_minutes"),
        "mean_fio2_value_age_minutes": mean("fio2_value_age_minutes"),
        "mean_synthetic_fio2_error_fraction": mean("synthetic_fio2_error_fraction"),
        "scheduled_oxygenation_count": len(acute),
        "recorded_oxygenation_count": len(recorded),
        "convertible_oxygenation_count": len(converted),
        "denominator_linked_count": len(linked),
        "eligible_oxygenation_count": len(eligible),
        "eligible_observation_fraction": len(eligible) / len(acute) if acute else None,
        "first_exclusion_counts": dict(
            Counter(e["first_exclusion"] for e in acute if not e["qualifies_acute"])
        ),
        "baseline_scheduled_count": sum(e.get("block") == "baseline" for e in events),
        "baseline_window_scheduled_count": len(baseline),
        "selected_day_scheduled_count": len(day) if selected else None,
        "selected_day_qualifying_count": sum(e["qualifies_baseline"] for e in day)
        if selected
        else None,
        "selected_baseline_day": selected["bin_start"] if selected else None,
    }


def metrics_v3():
    metrics = dict(METRICS)
    metrics["baseline_score"] = ("score", lambda r: r["baseline_algorithm_score"], "all_patients")
    for name in (
        "scheduled_oxygenation_count",
        "recorded_oxygenation_count",
        "convertible_oxygenation_count",
        "denominator_linked_count",
        "eligible_oxygenation_count",
        "baseline_scheduled_count",
        "baseline_window_scheduled_count",
        "selected_day_scheduled_count",
        "selected_day_qualifying_count",
    ):
        metrics[name] = ("records", lambda r, k=name: r[k], f"nonmissing:{name}")
    metrics["eligible_observation_fraction"] = (
        "fraction",
        lambda r: r["eligible_observation_fraction"],
        "nonmissing:eligible_observation_fraction",
    )
    for name, unit in [
        ("mean_fio2_source_age_minutes", "minutes"),
        ("mean_fio2_value_age_minutes", "minutes"),
        ("mean_synthetic_fio2_error_fraction", "fraction"),
    ]:
        metrics[name] = (unit, lambda r, k=name: r[k], f"nonmissing:{name}")
    for c in C_STRATA:
        metrics[f"sofa_eligibility_C{c}"] = (
            "probability",
            lambda r, c=c: eligibility(
                r["algorithm_score"],
                r["baseline_algorithm_score"],
                r["delta_evaluable"] is not None,
                c,
            )[0],
            "all_patients",
        )
        metrics[f"sofa_eligibility_evaluable_C{c}"] = (
            "probability",
            lambda r, c=c: (
                eligibility(
                    r["algorithm_score"],
                    r["baseline_algorithm_score"],
                    r["delta_evaluable"] is not None,
                    c,
                )[1]
                == "eligible"
            ),
            "all_patients" if c == "ge2" else "acute_and_baseline_evaluable",
        )
    return metrics


def summarize_v3(scores, comparator_id):
    result = summarize_paired_scores(
        scores, comparator_id, metrics=metrics_v3(), common_probabilities=True
    )
    groups = {}
    for row in scores:
        groups.setdefault(row["condition_id"], {})[row["patient_id"]] = row
    base = groups[comparator_id]
    for condition, rows in sorted(groups.items()):
        for c in C_STRATA:
            cells = {(a, b): [] for a in STATES for b in STATES}
            for patient in sorted(rows):
                states = [
                    eligibility(
                        r["algorithm_score"],
                        r["baseline_algorithm_score"],
                        r["delta_evaluable"] is not None,
                        c,
                    )[1]
                    for r in (base[patient], rows[patient])
                ]
                cells[tuple(states)].append(patient)
            for (before, after), patients in cells.items():
                result["transitions"].append(
                    {
                        "experiment_run_id": rows[next(iter(rows))]["experiment_run_id"],
                        "condition_id": condition,
                        "comparator_id": comparator_id,
                        "table": f"eligibility_C{c}",
                        "comparator_state": before,
                        "variant_state": after,
                        "count": len(patients),
                        "denominator": len(rows),
                        "patient_ids": patients,
                    }
                )
    return result
