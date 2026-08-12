# Changelog

## [Unreleased]

### Fixed

- Preserve DigiKey OAuth and Product API failures as `provider_error` instead
  of reporting false `not_found` responses.

### Added

- Add sanitized structured failure details to service envelopes while keeping
  the existing human-readable `error` field.

## [2026.6.5] - 2026-06-05

### Changed

- Switched release identity to date-based version `2026.6.5` and tag
  `v2026-06-05`.
- Renamed the PyPI distribution to `supply-chain-monkey` while keeping the
  public import package as `scm`.
- Documented the two repo surfaces: `scm.client` for consumers and
  `scm.server` for the deployed Appliku service.

### Added

- Added a PyPI Trusted Publishing workflow for the `pypi` GitHub environment.
- Added release metadata checks for date-based versioning and trusted
  publisher workflow configuration.

## [1.0.1] - 2026-06-05

### Changed

- Added the `wn-dev-std` Python package baseline, Rack release signoff,
  Ruff/Pyright configuration, root hygiene files, and standard docs entry
  points.
- Moved service runtime dependencies into base project dependencies so Appliku's
  managed `uv sync --frozen` path does not rely on development dependencies.
- Removed stale `supply_chain_monkey` and provider-level `.env` compatibility
  references from executable tests and provider code.

### Added

- Added L99 Appliku deployment contract checks for `appliku.yml`,
  `package = false`, manifest-only dependency sync, and runtime import through
  `PYTHONPATH=src/py`.

## [1.0.0] - 2026-03-25

### Added

- Initial standalone `scm` service, shared contract models, Python client, and
  Appliku deployment configuration.
