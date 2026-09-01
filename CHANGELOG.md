# Changelog

## [2026.9.1] - 2026-09-01

### Added

- Establish TypeSpec as the structural contract authority and generate the
  OpenAPI, JSON Schema, Python-model, contract-catalog, and Rust-model
  projections from it.
- Add a secure asynchronous Rust client and the `scm` test CLI with generic
  multi-provider search, JSON output, and a concise human-readable results
  table.
- Serve the canonical TypeSpec OpenAPI document and its Swagger explorer next
  to FastAPI's runtime OpenAPI, Swagger, and ReDoc views.
- Add executable contract-documentation coverage, generated-artifact checks,
  Rust doctests, and an isolated immutable-Git consumer proof.

### Fixed

- Restore JLCPCB and LCSC generic searches, including the LCSC C-number
  resolution path used by JLCPCB results.
- Preserve requested supplier identity and result bounds through provider
  fallback pipelines.
- Sanitize untrusted provider text in CLI table and error output.

### Changed

- Harden the documentation map, API exploration guide, Python/Rust consumption
  instructions, and generated-code ownership boundaries.

## [2026.8.12] - 2026-08-12

### Fixed

- Preserve DigiKey OAuth and Product API failures as `provider_error` instead
  of reporting false `not_found` responses.
- Keep wheel and source distributions on Core Metadata 2.4 until the release
  upload toolchain accepts Core Metadata 2.5.

### Added

- Add sanitized structured failure details to service envelopes while keeping
  the existing human-readable `error` field.
- Display those provider diagnostics on the demo/status page, including the
  error code, retryability, upstream HTTP status, and upstream request ID.

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
