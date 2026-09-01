# Supply Chain Monkey Rust workspace

This workspace provides typed Rust access to the SCM v1 service. It has no
deployment role; the Python service on repository branch `production` remains
the Appliku boundary.

| Package | Rust name | Purpose | Published? |
| --- | --- | --- | --- |
| `supply-chain-monkey-contracts` | `scm_contracts` | Generated models and strict bounded codec | No |
| `supply-chain-monkey-client` | `scm_client` | Secure asynchronous HTTP client | No |
| `supply-chain-monkey-cli` | `scm` binary | Interactive proof and test client | No |
| `scm-codegen` | `scm-codegen` | Repository-only deterministic generator | Never |

Start with the [client guide](src/scm-client/README.md) for library use or the
[CLI guide](src/scm-cli/README.md) for interactive searches.

## Immutable Git dependency

Until the crates are separately authorized and published, consumers can pin
the reviewed source commit. The package alias preserves the ergonomic
`scm_client` import:

```toml
[dependencies]
scm-client = { package = "supply-chain-monkey-client", git = "https://github.com/wavenumber-eng/supply-chain-monkey.git", rev = "e7bc0587e7a4b6435b993ce982505fb604861d20" }
tokio = { version = "1.53.1", features = ["macros", "rt-multi-thread"] }
```

Commit `e7bc0587e7a4b6435b993ce982505fb604861d20` is immutable and contains both
the client and its path-resolved contracts dependency. Do not replace `rev`
with a branch, a sibling checkout, or a moving tag. Commit `Cargo.lock` in the
consumer. The crates retain SemVer `0.1.0`; the SCM service uses an independent
date version.

Consumers need Rust 1.96 or newer. SCM development and release proofs select
the repository-pinned Rust 1.96.1 toolchain.

After that revision is reachable from the remote repository, prove the exact
dependency from a clean temporary project by running this from the repository
root:

```powershell
uv run python scripts/prove-git-rust-client.py
```

## Workspace development

From this directory:

```powershell
cargo fmt --all -- --check
cargo run -p scm-codegen --locked -- --check
cargo check --workspace --all-targets --all-features --locked
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
cargo test --workspace --all-features --locked
cargo test --workspace --doc --locked
$env:RUSTDOCFLAGS = "-D warnings"
cargo doc --workspace --no-deps --locked --open
```

Handwritten public APIs deny missing documentation. Generated models are
projections whose semantic descriptions originate in TypeSpec; never edit files
under `src/scm-contracts/src/generated` or `src/scm-contracts/schema` directly.

Use the pinned toolchain and locked commands documented in
[the Rust standard](docs/design/rust-standard.html). Dependency advisories,
SPDX license expressions, yanked packages, and source registries are governed
by `deny.toml`.
