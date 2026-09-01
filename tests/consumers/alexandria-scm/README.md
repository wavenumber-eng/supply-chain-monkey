# Alexandria SCM consumer proof

This standalone crate is the reviewed downstream shape for Alexandria's
future Rust-only SCM broker. It is deliberately not an Alexandria workspace
member or production route: Alexandria's own active plan still gates supplier
runtime integration.

The manifest names the registry boundary `scm-client = "=0.1.0"` and contains
no machine path. `scripts/prove-artifact-candidates.py` copies this crate into
an isolated directory, temporarily patches that dependency to the extracted
`scm-client` and `scm-contracts` candidate archives, and runs Clippy plus all
tests with a fresh Cargo target. The proof covers missing configuration,
unreachable SCM, mixed provider outcomes, cancellation, successful concurrent
search, and authorization-header-only credential transport.

A normal committed Alexandria workspace dependency remains blocked until the
accepted SCM source is reachable by an immutable Git revision or the crates
are published. That release-resolution step must not be replaced by a sibling
checkout path.

