# Accepted source and scientific decisions

The user explicitly adopted the following implementation scope on 2026-09-21.
These decisions replace the draft's current-source and Oracle prerequisites;
they do not establish unknown deployment facts.

| ID | Accepted decision |
|---|---|
| D01 | Historical commit `e8b4de0b6e898e94d7ad091796a4aaea1df96231` is the specification. Pin file hashes. Label historical and not execution-validated; current production status remains unknown. |
| D02 | Reproduce active historical zero-filled component rules, inclusive endpoints, componentwise nonnegative changes; maintain independent evidence availability. |
| D03 | Start with normalized timestamp values, supplied support episodes/flags and resolved encounter keys. Upstream extraction, clinical-documentation classification and encounter-context derivation are excluded. |
| D04 | External SQL execution is a separate future milestone. It does not block this phase and is not marked passed without an actual execution receipt. |
| D05 | V3 requests/bundles for new context and results; preserve v2 scientific meanings/import and old reference artifacts. Scientific identity and qualification are separate. |
| D06 | Three conditional C strata, patient-level uncertainty, 48 frozen stochastic references at N=2000, previews N=200, seed 173203; no effect-seeking tuning. |

Synthetic references declare UTC. This is a modeling clock choice and does not
identify the historical deployment timezone. Altered rule profiles are modified
experiments and cannot inherit an unmodified source-profile qualification.

Future external validation must identify the approved source, operator/boundary,
source/adapter/fixture hashes, runtime and timezone, intermediate outputs and
prespecified tolerances. Source mapping alone cannot establish SQL parity.
