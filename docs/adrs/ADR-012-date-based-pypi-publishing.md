# ADR-012: Date-Based PyPI Publishing

## Status

Accepted

## Context

Supply Chain Monkey is both a deployed Wavenumber service and a reusable client
library for applications such as `lib_cruncher`. The repository needs a public
package identity without exposing deployment credentials or making the
deployment branch the development path.

## Decision

- Use date-based package versions: `YYYY.M.D`.
- Use release tags: `vYYYY-MM-DD`.
- Publish the PyPI distribution as `supply-chain-monkey`.
- Keep the Python import package as `scm`.
- Publish through PyPI Trusted Publishing from GitHub Actions, using the
  `pypi` GitHub environment and no long-lived PyPI token.
- Keep `dev` as the integration branch, `main` as the public source branch, and
  `production` as the Wavenumber Appliku deployment branch.
- Update `production` only through protected PR/merge flow.

## Consequences

- Consumers depend on `supply-chain-monkey[client]` and import `scm`.
- PyPI must be configured with a pending or normal trusted publisher for:
  - owner: `wavenumber-eng`
  - repository: `supply-chain-monkey`
  - workflow: `release.yml`
  - environment: `pypi`
- Release signoff must verify the date-version/tag relationship and trusted
  publishing workflow configuration.
