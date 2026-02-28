from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from sofa_resp_sim.web.app_services import build_uncertainty_table, run_single_scenario
from sofa_resp_sim.web.view_model import default_run_request


def test_build_uncertainty_table_schema_and_score_coverage():
    request = replace(default_run_request(), n_reps=75, seed=41)
    _, replicates = run_single_scenario(request)

    reference = pd.Series(
        [0.1, 0.15, 0.4, 0.25, 0.1],
        index=[f"p_sofa_{score}" for score in range(5)],
    )
    uncertainty = build_uncertainty_table(
        replicates=replicates,
        reference_probs=reference,
        n_bootstrap=150,
        ci_level=0.95,
        seed=202,
    )

    assert uncertainty.columns.tolist() == [
        "score",
        "p_scenario",
        "ci_lower",
        "ci_upper",
        "p_reference",
        "delta_vs_reference",
    ]
    assert uncertainty["score"].tolist() == [0, 1, 2, 3, 4]
    assert uncertainty.notna().all().all()


def test_uncertainty_delta_equals_scenario_minus_reference():
    request = replace(default_run_request(), n_reps=90, seed=12)
    _, replicates = run_single_scenario(request)

    reference = pd.Series(
        [0.2, 0.2, 0.2, 0.2, 0.2],
        index=[f"p_sofa_{score}" for score in range(5)],
    )
    uncertainty = build_uncertainty_table(
        replicates=replicates,
        reference_probs=reference,
        n_bootstrap=150,
        ci_level=0.95,
        seed=17,
    )

    expected_delta = uncertainty["p_scenario"] - uncertainty["p_reference"]
    assert np.allclose(uncertainty["delta_vs_reference"], expected_delta)
