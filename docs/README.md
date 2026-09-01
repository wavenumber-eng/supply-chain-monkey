# Supply Chain Monkey documentation

Use this map to choose the documentation surface that matches your task.

| Task | Start here |
| --- | --- |
| Run or explore the HTTP service | [API exploration](guides/API_EXPLORATION.md) |
| Use the Python client | [Root client example](../README.md#python-client) |
| Use the Rust client | [Rust client guide](../rust/src/scm-client/README.md) |
| Use the `scm` command | [Rust CLI guide](../rust/src/scm-cli/README.md) |
| Understand the wire contract | [SCM v1 contract inventory](scm/design/v1-contract-inventory.md) |
| Author or regenerate contracts | [TypeSpec authority ADR](scm/adr/scm-adr-0013-typespec-wire-authority-and-generated-rust-client-boundary.md) |
| Understand Rust distribution | [Rust release ADR](scm/adr/scm-adr-0014-rust-release-distribution.md) |
| Contribute and run signoff | [Contributing guide](../CONTRIBUTING.md) |
| Review releases | [Release index](releases/README.md) and [current release](releases/2026-09-01.md) |
| Review current work | [Plans](plans/README.md) |

Authored contract source lives in `src/tsp/scm/v1/main.tsp`. Generated files
under `contracts/scm/v1/generated`, `src/py/scm/generated/v1`, and
`rust/src/scm-contracts/src/generated` are checked-in projections and must not
be edited by hand.

Repository documentation and examples never contain a real service URL, bearer
token, or provider credential. Configuration belongs in process environment.
