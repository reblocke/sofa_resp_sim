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
