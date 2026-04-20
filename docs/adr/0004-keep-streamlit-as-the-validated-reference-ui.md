# Keep Streamlit as the validated reference UI

- Status: accepted
- Date: 2026-04-20

## Context and Problem Statement

The repository already contains a functioning Streamlit applet and supporting service layer. A future API/frontend split may be useful, but the current applet is the validated and testable user-facing surface today.

## Decision Drivers

- preserve a working validation surface,
- avoid unnecessary architectural churn,
- keep UI work close to the current scientific workflow.

## Considered Options

- replace Streamlit immediately
- keep Streamlit as the current validated reference UI
- maintain both a Streamlit applet and a new frontend immediately

## Decision Outcome

Chosen option: keep Streamlit as the validated reference UI for now.

## Consequences

### Positive
- lower immediate complexity
- direct fit with current tests and docs
- easier to add native Streamlit smoke tests

### Negative
- future production deployment may still benefit from a separate API/frontend architecture
