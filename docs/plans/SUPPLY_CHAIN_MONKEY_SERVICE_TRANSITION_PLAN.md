# Completed Plan: Standalone Service Transition

## Status

Completed. Supply Chain Monkey is now a standalone repository with one FastAPI
service and one reusable Python client package.

## Current Shape

- Repository: `wavenumber-eng/supply-chain-monkey`
- PyPI distribution: `supply-chain-monkey`
- Python import package: `scm`
- Client surface: `scm.client` and `scm.models`
- Server surface: `scm.server`
- Deployment target: Appliku on the `production` branch

## Branch Model

- `dev`: integration and testing branch
- `main`: public source branch
- `production`: Wavenumber deployment branch

`production` should stay aligned with `main`, but it is not a development
branch. Changes should move through protected PR/merge flow.

## Deployment Boundary

The deployed service owns supplier credentials, provider routing, and
supplier-specific behavior. Consumer applications call it over HTTP and should
not import provider adapters directly.
