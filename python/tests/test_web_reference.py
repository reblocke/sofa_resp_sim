from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sofa_resp_sim.web.reference import (
    REQUIRED_PROBABILITY_COLUMNS,
    load_builtin_reference,
)


def test_load_builtin_reference_returns_normalized_probabilities():
    reference_path = (
        Path(__file__).resolve().parents[2] / "artifacts" / "resp_sofa_sim_summary.csv"
    )

    reference = load_builtin_reference(reference_path)

    assert list(reference.columns) == REQUIRED_PROBABILITY_COLUMNS
    assert reference.shape == (1, 5)
    assert reference.loc[0].sum() == pytest.approx(1.0)


def test_load_builtin_reference_rejects_missing_probability_columns(tmp_path):
    csv_path = tmp_path / "bad_reference.csv"
    pd.DataFrame(
        [
            {
                "p_sofa_0": 0.2,
                "p_sofa_1": 0.2,
                "p_sofa_2": 0.2,
                "p_sofa_3": 0.2,
            }
        ]
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="missing required probability columns"):
        load_builtin_reference(csv_path)


def test_load_builtin_reference_normalizes_non_unit_sum(tmp_path):
    csv_path = tmp_path / "count_like_reference.csv"
    pd.DataFrame(
        [
            {
                "p_sofa_0": 1,
                "p_sofa_1": 1,
                "p_sofa_2": 1,
                "p_sofa_3": 1,
                "p_sofa_4": 1,
            }
        ]
    ).to_csv(csv_path, index=False)

    reference = load_builtin_reference(csv_path)

    for column in REQUIRED_PROBABILITY_COLUMNS:
        assert reference.loc[0, column] == pytest.approx(0.2)
