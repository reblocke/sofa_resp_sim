import pytest

from sofa_resp_sim.core.experiment_config import (
    SCHEMA_VERSION,
    ScenarioConfig,
)
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request


def request(**changes):
    return normalize_experiment_request({"schema_version": SCHEMA_VERSION, **changes})


def test_normalized_roundtrip_and_condition_identity():
    first = request(
        conditions=[
            {"label": "Less frequent", "overrides": {"observation": {"interval_minutes": 60}}}
        ]
    )
    assert request(**first.to_dict()) == first
    extended = request(**{**first.to_dict(), "replicates": 1000})
    assert extended.comparator.condition_id == first.comparator.condition_id
    assert extended.conditions[0].condition_id == first.conditions[0].condition_id
    assert extended.run_id != first.run_id


@pytest.mark.parametrize(
    "changes",
    [
        {"unexpected": 1},
        {"schema_version": "v99"},
        {"rng_version": "new"},
        {"seed": True},
        {"seed": -1},
        {"replicates": 1.5},
        {"replicates": 0},
        {"replicates": float("inf")},
        {"primary_outcome": "accuracy"},
        {"conditions": [{"label": "Comparator"}]},
        {"conditions": "not an array"},
        {"base": {"observation": {"noise_sd_pct": float("nan")}}},
        {"base": {"observation": {"interval_minutes": 1.5}}},
        {"base": {"generator": {"tau_minutes": -1}}},
        {"base": {"generator": {"mean_pct": True}}},
        {"base": {"generator": {"unknown": 0}}},
        {"base": {"support": {"label": "IMV", "fio2_fraction": 50}}},
        {"base": {"support": {"label": "UNKNOWN"}}},
        {"base": {"support": {"label": "LOW_FLOW", "flow_lpm": 4}}},
        {"base": {"scoring": {"timezone": "not/a/timezone"}}},
        {"base": {"horizon": {"admit_dts": "2024-01-01T12:37:00"}}},
        {"base": {"horizon": {"end_minute": -400}}},
        {"base": {"documentation": {"recorded_delay_minutes": -1}}},
        {"conditions": [{"label": "x", "overrides": {"generator": {"bogus": 1}}}]},
    ],
)
def test_invalid_scientific_requests_fail(changes):
    with pytest.raises(ValueError):
        request(**changes)


def test_explicit_zero_variability_and_unknown_support_are_valid():
    result = request(
        base={
            "generator": {"marginal_sd_pct": 0, "tau_minutes": 0},
            "observation": {"noise_sd_pct": 0},
            "support": {"label": "UNKNOWN", "fio2_fraction": None},
        }
    )
    assert result.base.generator.marginal_sd_pct == 0
    assert result.base.support.fio2_fraction is None


def test_scientific_overrides_inherit_actual_base():
    base = ScenarioConfig.from_dict({"generator": {"mean_pct": 87}})
    changed = base.override({"observation": {"interval_minutes": 60}})
    assert changed.generator.mean_pct == 87
    assert changed.observation.interval_minutes == 60


def test_integral_json_numbers_normalize_consistently():
    assert request(replicates=2.0, seed=0.0) == request(replicates=2, seed=0)


def test_overlap_and_conflicting_prescribed_generation_rejected():
    with pytest.raises(ValueError, match="overlap"):
        ScenarioConfig.from_dict(
            {
                "generator": {
                    "episode_rate_per_hour": 0,
                    "prescribed_episodes": [
                        {"start_minute": 0, "end_minute": 30, "depth_pct_points": 5},
                        {"start_minute": 20, "end_minute": 40, "depth_pct_points": 5},
                    ],
                }
            }
        )
    with pytest.raises(ValueError, match="require marginal"):
        ScenarioConfig.from_dict(
            {"generator": {"prescribed_trajectory": [{"minute": 0, "spo2_pct": 90}]}}
        )
