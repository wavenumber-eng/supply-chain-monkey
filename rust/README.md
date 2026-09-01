# Supply Chain Monkey Rust workspace

This workspace contains the generated SCM v1 structural contracts, async Rust
client, proof CLI, and unpublished code generator. It has no deployment role;
the Python service on the repository `production` branch remains the deployed
Appliku boundary.

Use the pinned toolchain and locked commands documented in
`docs/design/rust-standard.html`.

Dependency advisories, SPDX license expressions, yanked packages, and source
registries are governed by `deny.toml`. Install the exact review tool with
`cargo install --locked cargo-deny --version 0.20.2`, then run
`cargo deny --locked --all-features check advisories licenses sources`.
