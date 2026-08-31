# Supply Chain Monkey Rust Agent Guide

- Treat `../contracts/scm/v1/generated` as generated wire authority; never hand-edit it.
- Keep generated Rust structural models in `src/scm-contracts/src/generated`.
- Keep transport and credentials out of `scm-contracts`.
- Do not add the deprecated query-token stream operation to `scm-client` or `scm-cli`.
- Never place bearer tokens in URLs, command arguments, logs, errors, or `Debug` output.
- Do not weaken TLS certificate validation or enable redirects.
- Run locked Cargo format, check, Clippy, tests, doctests, and rustdoc before signoff.
