# Use MADR for project decisions

- Status: accepted
- Date: 2026-04-20

## Context and Problem Statement

The repository already contains milestone notes and planning documents, but important architectural and workflow decisions are not recorded in a consistent, durable format.

## Decision Drivers

- keep major decisions discoverable,
- reduce repeated re-litigation of settled repo choices,
- make the repository easier for collaborators and agents to understand.

## Considered Options

- free-form notes only
- ad hoc markdown files per decision
- MADR

## Decision Outcome

Chosen option: MADR.

## Consequences

### Positive
- lightweight and readable
- easy to version in git
- good fit for package/environment/UI boundary decisions

### Negative
- requires maintainers to keep decisions current
