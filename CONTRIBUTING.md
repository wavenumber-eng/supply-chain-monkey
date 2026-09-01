# Contributing

Use `dev` as the integration branch and `production` only as the deployed
release branch. Keep Appliku changes narrow and never develop directly on
`production`.

Start with the [documentation map](docs/README.md). Authored contracts live in
`src/tsp`; generated contracts, Python models/resources, and Rust models must
not be edited directly.

```powershell
uv sync --group dev
uv run pytest -q
uv run rack run L99_signoff
```

For contract or Rust changes:

```powershell
npm ci
npm run check:typespec
npm run check:contracts
npm run check:python-generation

Push-Location rust
cargo fmt --all -- --check
cargo run -p scm-codegen --locked -- --check
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
cargo test --workspace --all-features --locked
cargo test --workspace --doc --locked
$env:RUSTDOCFLAGS = "-D warnings"
cargo doc --workspace --no-deps --locked
Pop-Location
```

Do not commit secrets, generated build output, local virtual environments, or
live supplier response dumps. Live provider checks require explicit credentials
and `SUPPLY_CHAIN_ENABLE_LIVE_TESTS=1`.

Documentation examples use loopback or fictional hosts and environment-based
tokens. The deprecated stream query token must never appear in logs, fixtures,
browser history, or shared URLs.
