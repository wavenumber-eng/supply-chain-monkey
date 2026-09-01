# Alexandria SCM consumer proof

This standalone crate is the reviewed downstream shape for Alexandria's
future Rust-only SCM broker. It is deliberately not an Alexandria workspace
member or production route: Alexandria's own active plan still gates supplier
runtime integration.

The manifest aliases the registry package
`supply-chain-monkey-client = "=0.1.0"` as the ergonomic Rust dependency
`scm-client` and contains no machine path. `scripts/prove-artifact-candidates.py`
copies this crate into an isolated directory, temporarily patches that
dependency to the extracted `supply-chain-monkey-client` and
`supply-chain-monkey-contracts` candidate archives, and runs Clippy plus all
tests with a fresh Cargo target. The proof covers missing configuration,
unreachable SCM, mixed provider outcomes, cancellation, successful concurrent
search, and authorization-header-only credential transport.

Before crates.io publication, a normal Alexandria workspace can use the
reviewed immutable Git dependency documented in the Rust client README:

```toml
scm-client = { package = "supply-chain-monkey-client", git = "https://github.com/wavenumber-eng/supply-chain-monkey.git", rev = "e7bc0587e7a4b6435b993ce982505fb604861d20" }
```

The release proof must resolve that revision from the remote repository in a
clean temporary project with no sibling checkout or machine path. Alexandria
should commit its resulting `Cargo.lock`. A branch or moving tag is not an
acceptable substitute for `rev`.
