---
name: implementation-strategy
description: Use when changing respiratory scoring logic, simulation assumptions, public schemas, CLI contracts, package layout, or any other change that alters system behavior rather than presentation alone. Do not use for small doc-only or comment-only edits.
---

Before editing code:

1. Identify the source-of-truth module(s).
2. State the invariant(s) that must remain true.
3. Identify:
   - tests to update or add,
   - docs to update,
   - artifacts to update,
   - any API or schema surfaces affected.
4. Choose the smallest cohesive change set.
5. Only then edit.

Outputs to produce during the task:
- a short plan,
- the changed files,
- the verification commands,
- any unresolved risks.

Specific to this repo:
- scoring truth lives in `resp_scoring.py`, `resp_utils.py`, and `resp_simulation.py`
- the Streamlit layer must not diverge from those modules
- package identity must remain `sofa_resp_sim`
