from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sofa_resp_sim.web.reference import (
    REQUIRED_PROBABILITY_COLUMNS,
    load_builtin_reference,
    normalize_reference_distribution,
)


def test_load_builtin_reference_returns_normalized_probabilities():
    reference_path = (
        Path(__file__).resolve().parents[2] / "artifacts" / "resp_sofa_sim_summary.csv"
    )

    reference = load_builtin_reference(reference_path)

    assert list(reference.columns) == REQUIRED_PROBABILITY_COLUMNS
    assert reference.shape == (1, 5)
    assert reference.loc[0].sum() == pytest.approx(1.0)


def test_load_builtin_reference_rejects_missing_supported_schemas(tmp_path):
    csv_path = tmp_path / "bad_reference.csv"
    pd.DataFrame(
        [
            {
                "a": 1,
                "b": 2,
            }
        ]
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="must include either probability columns"):
        load_builtin_reference(csv_path)


def test_normalize_reference_distribution_probability_form():
    frame = pd.DataFrame(
        [
            {
                "p_sofa_0": 1,
                "p_sofa_1": 2,
                "p_sofa_2": 3,
                "p_sofa_3": 4,
                "p_sofa_4": 5,
            }
        ]
    )

    reference = normalize_reference_distribution(frame)

    assert list(reference.columns) == REQUIRED_PROBABILITY_COLUMNS
    assert reference.shape == (1, 5)
    assert reference.loc[0].sum() == pytest.approx(1.0)


def test_normalize_reference_distribution_count_form_happy_path():
    frame = pd.DataFrame(
        [
            {"sofa_pulm": 0, "count": 10},
            {"sofa_pulm": 2, "count": 5},
            {"sofa_pulm": 2, "count": 5},
            {"sofa_pulm": 4, "count": 10},
        ]
    )

    reference = normalize_reference_distribution(frame)

    assert list(reference.columns) == REQUIRED_PROBABILITY_COLUMNS
    assert reference.shape == (1, 5)
    assert reference.loc[0, "p_sofa_0"] == pytest.approx(10 / 30)
    assert reference.loc[0, "p_sofa_1"] == pytest.approx(0)
    assert reference.loc[0, "p_sofa_2"] == pytest.approx(10 / 30)
    assert reference.loc[0, "p_sofa_3"] == pytest.approx(0)
    assert reference.loc[0, "p_sofa_4"] == pytest.approx(10 / 30)


def test_normalize_reference_distribution_prefers_probability_schema_when_both_present():
    frame = pd.DataFrame(
        [
            {
                "p_sofa_0": 0.6,
                "p_sofa_1": 0.1,
                "p_sofa_2": 0.1,
                "p_sofa_3": 0.1,
                "p_sofa_4": 0.1,
                "sofa_pulm": 4,
                "count": 100,
            }
        ]
    )

    reference = normalize_reference_distribution(frame)

    assert reference.loc[0, "p_sofa_0"] == pytest.approx(0.6)
    assert reference.loc[0, "p_sofa_4"] == pytest.approx(0.1)


@pytest.mark.parametrize(
    "frame, error",
    [
        (
            pd.DataFrame([{"sofa_pulm": 5, "count": 1}]),
            r"must be in \[0, 4\]",
        ),
        (
            pd.DataFrame([{"sofa_pulm": 1.5, "count": 1}]),
            "must be integers 0..4",
        ),
        (
            pd.DataFrame([{"sofa_pulm": 1, "count": -1}]),
            "must be non-negative",
        ),
        (
            pd.DataFrame([{"sofa_pulm": 1, "count": 0}]),
            "must sum to a positive value",
        ),
        (
            pd.DataFrame(columns=["sofa_pulm", "count"]),
            "Reference table is empty",
        ),
    ],
)
def test_normalize_reference_distribution_count_form_errors(frame, error):
    with pytest.raises(ValueError, match=error):
        normalize_reference_distribution(frame)
