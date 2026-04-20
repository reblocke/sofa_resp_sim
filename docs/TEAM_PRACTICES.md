# Team practices

## Coding standards

- Prefer descriptive names.
- Keep functions small and single-purpose.
- Keep numerical core logic pure and testable.
- Avoid hidden state and undocumented assumptions.
- Keep JavaScript focused on UI, worker orchestration, and rendering returned
  Python payloads.

## Review standards

Every substantive change should include:
- code changes,
- validation evidence,
- doc updates if behavior or workflow changed.

Minimum local verification for ordinary changes:

```bash
make test
```

For packaging, browser-facing, release, or public-facing documentation changes,
also run:

```bash
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

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
