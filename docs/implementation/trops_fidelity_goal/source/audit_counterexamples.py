"""Independent numerical checks for the 2026-09-21 SOFA refactor audit.

This is NOT an execution of the repository test suite or the Oracle SQL.
It reconstructs the specific equations, ordering keys, and interval calculations
read from pinned source files. All input records below are synthetic.

sofa_resp_sim: 944a45eb801cc4f96e0a98d80f62af63dd452afe
historical TROPS: e8b4de0b6e898e94d7ad091796a4aaea1df96231
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import binomtest


def main() -> None:
    checks: dict = {}

    # Reconstruct the implemented stationary AR(1) equation in physical time.
    seed, n, mu, sigma, tau = 47031, 200_000, 94.0, 1.5, 30.0
    z = np.random.Generator(np.random.PCG64(seed)).standard_normal(n)
    phi = np.exp(-1.0 / tau)
    deviation = np.empty(n)
    deviation[0] = sigma * z[0]
    deviation[1:], _ = lfilter(
        [sigma * np.sqrt(1 - phi**2)], [1, -phi], z[1:],
        zi=[phi * deviation[0]],
    )
    x = mu + deviation
    actual_sd = float(x.std())
    lag30 = float(np.corrcoef(x[:-30], x[30:])[0, 1])
    checks['stationary_AR_equation'] = {
        'expected_marginal_sd': sigma, 'empirical_marginal_sd': actual_sd,
        'expected_lag30_correlation': float(np.exp(-1)),
        'empirical_lag30_correlation': lag30,
        'scope': 'Independent reconstruction of the published v2 equation; not pipeline execution',
    }
    assert abs(actual_sd - sigma) < 0.05
    assert abs(lag30 - np.exp(-1)) < 0.05

    # A prescribed episode is applied once, not recursively to the AR state.
    minutes = np.arange(0, 120)
    saturation = np.full(120, 96.0)
    saturation[(minutes >= 30) & (minutes < 60)] -= 5
    checks['episode_observation_schedules'] = {
        str(interval): {'observations': len(saturation[::interval]),
                        'minimum_observed': float(saturation[::interval].min())}
        for interval in (5, 15, 30, 60)
    }
    assert checks['episode_observation_schedules']['5']['minimum_observed'] == 91
    assert checks['episode_observation_schedules']['60']['minimum_observed'] == 96

    # Independent calculation of the repository's paired difference estimator.
    n_plus, n_minus, pairs = 30, 10, 100
    difference = (n_plus - n_minus) / pairs
    mcse = math.sqrt((n_plus + n_minus - pairs * difference**2) / (pairs * (pairs - 1)))
    plus = binomtest(n_plus, pairs).proportion_ci(.975, method='exact')
    minus = binomtest(n_minus, pairs).proportion_ci(.975, method='exact')
    zero = binomtest(0, 2000).proportion_ci(.95, method='wilson')
    checks['Monte_Carlo_calculations'] = {
        'paired_difference': difference, 'paired_MCSE': mcse,
        'conservative_paired_95_bounds': [float(plus.low-minus.high), float(plus.high-minus.low)],
        'Wilson_zero_of_2000_95_bounds': [float(zero.low), float(zero.high)],
    }
    assert difference == .2 and zero.high > 0

    # The historical SQL bins pre-admission records by TRUNC(relative days)-1.
    # V2 defaults to the calendar date. Same data, different selected baseline.
    admit = pd.Timestamp('2026-01-31T12:00:00Z')
    rows = [
        {'event': 'synthetic_morning', 'time': pd.Timestamp('2026-01-20T08:00:00Z'), 'score': 2},
        {'event': 'synthetic_evening', 'time': pd.Timestamp('2026-01-20T18:00:00Z'), 'score': 0},
    ]
    for row in rows:
        row['calendar_day'] = row['time'].normalize()
        row['SQL_day_index'] = math.trunc((row['time']-admit).total_seconds()/86400) - 1
    calendar_winner = max(rows, key=lambda r: (r['calendar_day'], r['score'], r['time']))
    sql_winner = max(rows, key=lambda r: (r['SQL_day_index'], r['score'], r['time']))
    checks['baseline_selection_counterexample'] = {
        'admission': admit.isoformat(),
        'events': [{**r, 'time':r['time'].isoformat(), 'calendar_day':r['calendar_day'].isoformat()}
                   for r in rows],
        'v2_calendar_baseline_score': calendar_winner['score'],
        'historical_SQL_baseline_score': sql_winner['score'],
        'scope': 'Ordering-key reconstruction, not execution against the warehouse',
    }
    assert calendar_winner['score'] == 2 and sql_winner['score'] == 0

    cutoff = admit.normalize() - pd.Timedelta(days=7)
    event = pd.Timestamp('2026-01-24T12:00:00Z')
    checks['baseline_cutoff_counterexample'] = {
        'cutoff': cutoff.isoformat(), 'event_time': event.isoformat(),
        'historical_SQL_eligible': bool(event <= cutoff),
        'v2_calendar_eligible': bool(event.normalize() <= cutoff),
    }
    assert not (event <= cutoff) and event.normalize() <= cutoff
    checks['acute_endpoint'] = {
        'minute': 1440, 'historical_SQL_inclusive': True,
        'bounded_analysis_v2_half_open': False,
        'interpretation': 'Intentional profile difference, not a newly introduced regression',
    }

    # TROPS sums nonnegative COMPONENT changes rather than clipping the total change.
    signed_components = np.array([1, -2, 1, 0, 0, 0])
    checks['componentwise_delta'] = {
        'synthetic_signed_component_changes': signed_components.tolist(),
        'sum_of_nonnegative_component_deltas': int(np.maximum(signed_components, 0).sum()),
        'nonnegative_delta_of_total_scores': int(max(signed_components.sum(), 0)),
    }
    assert checks['componentwise_delta']['sum_of_nonnegative_component_deltas'] == 2
    assert checks['componentwise_delta']['nonnegative_delta_of_total_scores'] == 0

    # A 24-hour baseline beginning at the default non-midnight admission clock
    # crosses two calendar dates; latest-day selection does not use all 24h.
    default_admit = pd.Timestamp('2024-01-01T12:37:00Z')
    baseline_start = default_admit - pd.Timedelta(days=30)
    baseline_times = pd.date_range(baseline_start, periods=96, freq='15min')
    latest_day = baseline_times[-1].normalize()
    checks['E5_calendar_opportunity'] = {
        'baseline_start': baseline_start.isoformat(),
        'total_scheduled_oxygenation_records': len(baseline_times),
        'latest_calendar_date_records': int(sum(t.normalize() == latest_day for t in baseline_times)),
        'caveat': 'Scheduled records only; actual qualifying counts also depend on conversion/documentation',
    }

    # Conditional marginal estimates may target different patient sets than the
    # paired both-evaluable contrast. This is a presentation issue, not wrong MCSE.
    comparator_deltas = [1, None]
    variant_deltas = [1, 0]
    comparator_observed = [x for x in comparator_deltas if x is not None]
    variant_observed = [x for x in variant_deltas if x is not None]
    pairs_evaluable = [(c, v) for c, v in zip(comparator_deltas, variant_deltas, strict=True)
                      if c is not None and v is not None]
    checks['evaluable_denominator_example'] = {
        'comparator_marginal_probability': sum(x >= 1 for x in comparator_observed)/len(comparator_observed),
        'variant_marginal_probability': sum(x >= 1 for x in variant_observed)/len(variant_observed),
        'common_evaluable_paired_difference': sum(int(v >= 1)-int(c >= 1) for c,v in pairs_evaluable)/len(pairs_evaluable),
        'paired_denominator': len(pairs_evaluable),
    }
    output = Path(__file__).with_name('audit_counterexamples.json')
    output.write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
