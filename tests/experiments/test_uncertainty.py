import pytest

from sofa_resp_sim.reporting.experiment_results import paired_binary, wilson_probability


def test_wilson_boundary_cases():
    zero = wilson_probability(0, 200)
    full = wilson_probability(200, 200)
    assert zero["lower"] == pytest.approx(0, abs=1e-15)
    assert zero["upper"] == pytest.approx(0.018845326377266575, abs=1e-12)
    assert full["lower"] == pytest.approx(1 - zero["upper"], abs=1e-12)
    assert full["upper"] == pytest.approx(1)


def test_paired_discordance_anchor():
    result = paired_binary(30, 10, 100)
    assert result["estimate"] == 0.2
    assert result["percentage_point_difference"] == 20
    assert result["mcse"] == pytest.approx(0.06030226891555272, abs=1e-12)
    assert result["lower"] == pytest.approx(0.013763053206362341, abs=1e-12)
    assert result["upper"] == pytest.approx(0.3700078964050354, abs=1e-12)
    reverse = paired_binary(10, 30, 100)
    assert reverse["lower"] == pytest.approx(-result["upper"])
    assert reverse["upper"] == pytest.approx(-result["lower"])


def test_zero_discordance_does_not_prove_identity():
    result = paired_binary(0, 0, 100)
    assert result["mcse"] == 0
    assert not result["structural_identity"]
    assert result["lower"] == pytest.approx(-0.042874030238438485, abs=1e-12)
    assert result["upper"] == pytest.approx(0.042874030238438485, abs=1e-12)


@pytest.mark.parametrize("n", [0, 1])
def test_small_n_is_explicitly_unavailable(n):
    for result in [wilson_probability(0, n), paired_binary(0, 0, n)]:
        assert result["lower"] is result["upper"] is result["mcse"] is None
        assert result["uncertainty_unavailable_reason"] == "fewer_than_two_patients"
        assert result["estimate"] == (0 if n else None)


@pytest.mark.parametrize("args", [(2, 0, 1), (0, -1, 5), (False, 0, 5)])
def test_invalid_discordance_counts_fail(args):
    with pytest.raises(ValueError):
        paired_binary(*args)
