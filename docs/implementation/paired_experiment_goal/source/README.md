# Respiratory SOFA Codex implementation goal

This packet specifies work to implement. It does not contain the new simulator or claim that the requested acceptance tests already pass.

Canonical GitHub issue: https://github.com/reblocke/sofa_resp_sim/issues/11

## Use

Open the `sofa_resp_sim` repository in your coding environment and provide `CODEX_GOAL.md` as the task. The GitHub issue contains the full specification. `IMPLEMENTATION_TICKET.md` is the downloadable version 1.0 snapshot; reconcile later issue revisions explicitly.

## Contents

- `IMPLEMENTATION_TICKET.md`: full scientific and behavioral contract, six experiments, deterministic rule explorer, schemas, compatibility boundaries, five milestones, and 28 acceptance criteria.
- `CODEX_GOAL.md`: paste-in execution goal.
- `ACCEPTANCE_CRITERIA.json`: machine-readable A01-A28, extracted from the ticket rather than independently rewritten.
- `NUMERICAL_CASES.json`: selected numerical acceptance examples. Interval values were calculated using the installed SciPy version identified in the file. Respiratory scoring values are specified from the audited formulas and fixtures, not from executing a new implementation.
- `GITHUB_ISSUE.json`: issue identity and audit anchor.
- `SHA256SUMS`: checksums for this packet's files, excluding the checksum file itself.

## Completion boundary

The implementer must produce working code and real example outputs. External clinical calibration, independent confirmation against the original SQL, and physiological treatment-response modeling are not established by this packet. No repository source code was changed while preparing it.

The proposed `resp-sofa-experiment` commands and new Make targets are implementation requirements, not commands claimed to exist at the audited starting commit.
