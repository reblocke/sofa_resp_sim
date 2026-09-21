# Codex goal

Implement `reblocke/sofa_resp_sim` issue #11:
https://github.com/reblocke/sofa_resp_sim/issues/11

Treat the full issue as the end-state contract, not a request for another audit or a planning-only response. The accompanying `IMPLEMENTATION_TICKET.md` is the version 1.0 snapshot. Read `AGENTS.md` and relevant repository instructions, then reconcile the ticket with the current checkout and preserve unrelated work.

Deliver a paired respiratory SOFA experimental workbench: generate each synthetic patient's underlying trajectory once; vary observation, documentation, or explicit scoring rules without unintentionally changing that patient; report paired effects and evidence availability; explain individual score changes; and export reproducible experiment bundles.

Work through milestones M0-M4 in cohesive increments. Preserve existing behavior as `legacy_py_v1`; place new scientific behavior behind explicit v2 contracts. Implement the six named experiments and deterministic rule explorer. Use the specified estimands, time and missingness semantics, random-stream invariants, and Monte Carlo methods. Internal organization is your choice; scientific scope and acceptance requirements are not.

Map A01-A28 to actual tests and artifacts in a concise status file. Run targeted verification while developing and full native/browser verification at integration boundaries. Completion requires generated experiment data, linked diagnostic traces, browser evidence, and clean-environment reproduction, not just passing schema tests.

Do not tune examples to force positive findings, silently alter legacy semantics, claim unavailable SQL or clinical validation, or weaken tests. Isolate genuine blockers and continue independent work. Report implemented, verified, and blocked items separately. Do not merge, publish a release, rewrite history, or change repository visibility without separate authorization.
