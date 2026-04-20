# Team practices

## Coding standards

- Prefer descriptive names.
- Keep functions small and single-purpose.
- Keep one level of abstraction per function where practical.
- Keep numerical core logic pure and testable.
- Avoid hidden state and undocumented assumptions.

## Review standards

Every substantive change should include:
- code changes,
- validation evidence,
- doc updates if behavior changed.

Minimum local verification for ordinary changes:

```bash
make check
```

For packaging, release, or public-facing documentation changes, also run:

```bash
uv run python -m build
uv run resp-sofa-sim --help
uv run pytest -q python/tests/test_streamlit_app_smoke.py
```

## Repository truthfulness rule

README, metadata, commands, and package names must match the actual code layout.
Do not allow stale names or placeholder metadata to linger.

## Artifacts

Checked-in artifacts must be:
- small,
- reproducible,
- documented,
- clearly labeled as canonical evidence, informative context, or deprecated scratch material.

## Decision records

Use ADRs under `docs/adr/` for decisions that affect:
- package layout,
- environment manager,
- UI architecture,
- artifact policy,
- provenance policy,
- release process.

## Public release checks

Before making a hosted repository public:
- verify `docs/PUBLIC_RELEASE_AUDIT.md` is current,
- confirm no tracked PHI, patient-level extracts, restricted data, secrets, or literature PDFs are present,
- check git history and provider PR refs for blobs that should not be redistributed,
- prefer publishing from a clean history if historical blobs cannot be purged reliably.
