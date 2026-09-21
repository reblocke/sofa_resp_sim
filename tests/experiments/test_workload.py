from unittest.mock import patch

from sofa_resp_sim.browser_contract import run_experiment_payload
from sofa_resp_sim.core.experiment_config import fingerprint
from sofa_resp_sim.core.observation import document_patient
from sofa_resp_sim.core.paired_simulation import generate_patient
from sofa_resp_sim.reporting.experiment_catalogue import CATALOGUE, STRATA, catalogue_request
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_workload import estimate_workload


def test_all_catalogue_previews_fit_the_declared_workload_envelope():
    for entry in CATALOGUE:
        for stratum in STRATA:
            work = estimate_workload(catalogue_request(entry, stratum))
            assert work["preview_allowed"], (entry, stratum, work)


def test_documented_event_estimate_matches_actual_shared_streams():
    request = catalogue_request("E5_opportunity", "hfnc", replicates=2)
    generators, observations = {}, {}
    for c in (request.comparator, *request.conditions):
        config = c.config
        key = fingerprint(
            {"generator": config.generator.to_dict(), "horizon": config.horizon.to_dict()}
        )
        if key not in generators:
            generators[key] = generate_patient(config.generator, config.horizon, request.seed, 0)
        fields = config.to_dict()
        fields.pop("scoring")
        observations[fingerprint(fields)] = len(document_patient(generators[key], config))
    work = estimate_workload(request)
    assert work["documented_events"] == 2 * sum(observations.values())
    assert work["latent_minutes"] == 2 * sum(
        len(b.minutes) for p in generators.values() for b in p.blocks
    )


def test_oversized_preview_rejects_before_generation_and_cli_remains_available():
    request = catalogue_request("E1_density", "room_air", replicates=201)
    with patch("sofa_resp_sim.reporting.experiment_service.generate_patient") as generate:
        result = run_experiment_payload({"request": request.to_dict()})
    generate.assert_not_called()
    assert not result["ok"]
    assert "resp-sofa-experiment run" in result["error"]["message"]
    # Allocation must also be bounded for small N with extreme horizons/density.
    raw = request.to_dict()
    raw["replicates"] = 1
    raw["base"]["horizon"]["end_minute"] = 1000000000
    raw["comparator"]["overrides"] = raw["base"]
    raw["conditions"] = []
    work = estimate_workload(normalize_experiment_request(raw))
    assert not work["preview_allowed"]
    assert "peak_latent_minutes_per_patient" in work["exceeded_limits"]
