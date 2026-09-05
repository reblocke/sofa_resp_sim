# Team practices

## Coding standards

- Prefer descriptive names.
- Keep functions small and single-purpose.
- Keep numerical core logic pure and testable.
- Avoid hidden state and undocumented assumptions.
- Keep JavaScript focused on UI, worker orchestration, and rendering returned
  Python payloads.

## Review standards

Substantive changes should include relevant validation evidence and documentation
updates when behavior or workflow changes.

- Documentation-only edits need affected-reference checks and `git diff --check`.
- Code changes need affected tests and lint/format checks for touched code. Use
  `make test` for shared numerical behavior or broader integration changes.
- Browser code, staging, worker, or payload changes need `make e2e`, which stages
  assets first; verify returned Python results and export contracts.
- Installation/build changes need `uv run python -m build`; console-entrypoint
  changes need `uv run resp-sofa-sim --help` and the affected CLI tests.
- Broad integration changes need `make verify`. Release/public-visibility work
  retains the complete checks in `docs/VALIDATION.md`.

## Repository truthfulness rule

README, metadata, commands, app deployment docs, and package names must match the
actual code layout. Do not allow stale names, inactive app references, or
placeholder metadata to linger in active docs.

## Artifacts

Checked-in artifacts must be:
- small,
- reproducible,
- documented,
- clearly labeled as canonical evidence, informative context, or deprecated
  scratch material.

Generated web assets under `web/assets/py/` and `web/assets/data/` are not
checked-in artifacts. Regenerate them with `make stage-web`.

## Decision records

Use ADRs under `docs/adr/` for decisions that affect:
- package layout,
- environment manager,
- browser/runtime architecture,
- artifact policy,
- provenance policy,
- release process.

## Public release checks

Before making a hosted repository public:
- verify `docs/PUBLIC_RELEASE_AUDIT.md` is current,
- confirm no tracked PHI, patient-level extracts, restricted data, secrets, or
  literature PDFs are present,
- check git history and provider PR refs for blobs that should not be
  redistributed,
- prefer publishing from a clean history if historical blobs cannot be purged
  reliably.
