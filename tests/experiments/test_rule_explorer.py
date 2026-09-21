import pytest

from sofa_resp_sim.reporting.rule_explorer import explore_rules


def test_conversion_unavailable_is_not_normal_zero():
    result = explore_rules({})
    cells = {c["input_value"]: c for c in result["cells"]}
    assert cells[49]["conversion_unavailable"] and cells[97]["conversion_unavailable"]
    assert cells[50]["pao2_calc_mmhg"] == 26.9
    assert cells[96]["pf_ratio_mmhg"] == 390
    assert cells[96]["encounter"]["algorithm_score"] == 1
    assert not result["monte_carlo"]


def test_measured_cutpoints_and_explicit_encounter_record_count():
    result = explore_rules(
        {
            "source": "measured_pao2",
            "values": [100, 200, 300, 400],
            "supports": [{"label": "IMV", "fio2_fraction": 1}],
        }
    )
    assert [c["raw_rubric"] for c in result["cells"]] == [3, 2, 1, 0]
    for records, expected in [(1, 0), (2, 2)]:
        cell = explore_rules(
            {
                "values": [90],
                "records": records,
                "supports": [{"label": "LOW_FLOW", "fio2_fraction": None, "flow_lpm": 4}],
            }
        )["cells"][0]
        assert cell["raw_rubric"] == 3
        assert cell["encounter"]["pre_suppression_score"] == 2
        assert cell["encounter"]["algorithm_score"] == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"values": [101]},
        {"values": []},
        {"records": 3},
        {"values": [float("nan")]},
        {"unknown": 1},
        {"supports": [{"mode": "assignment_stress_test"}]},
    ],
)
def test_invalid_explorer_inputs_fail(payload):
    with pytest.raises(ValueError):
        explore_rules(payload)
