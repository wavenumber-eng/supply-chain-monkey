# Changelog

## [Unreleased]

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
