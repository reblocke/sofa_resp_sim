# Prespecified illustrative experiment requests

`catalogue.json` describes 18 demonstrations and their limitations. `E1.json`
through `E6.json` contain 72 fully resolved requests across four separate support
strata, generated from `reporting/experiment_catalogue.py`. These are configurations,
not results. Reference execution is pending; do not infer findings from this folder.

The stochastic requests specify seed 173203 and 2,000 paired patients per stratum.
The deterministic E1 example has one patient. The E5 exact-replay control repeats
the same six-hour segment at the same UTC time of day within one calendar date;
independent stationary baseline/acute realizations have no zero-delta guarantee.

Regenerate with `uv run python scripts/freeze_experiment_catalogue.py`; verify with
`--check`. Never edit generated requests by hand. Edited interactive requests are
separate user scenarios and must preserve their fully normalized base when expanded.
