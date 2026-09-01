# scm

Small command-line proof for the public async Supply Chain Monkey Rust client.

Build or run it from the Rust workspace:

```powershell
cargo build -p supply-chain-monkey-cli --locked
cargo run -p supply-chain-monkey-cli --locked -- --help
```

Set `SCM_URL` or pass `--url`. Authenticated commands read the bearer token
only from `SCM_TOKEN`; there is intentionally no token command-line option.
Use `--json` for the complete typed envelope or the default stable summary for
interactive checks.

Search every configured provider concurrently and render a compact ASCII table:

```text
scm search RT685
```

Restrict the search with one or more repeatable provider filters:

```text
scm search RT685 --supplier LCSC --supplier Mouser
```

The default table shows supplier, manufacturer, MPN, supplier part number,
description, first price break, and stock. `--json` emits the stable
multi-provider result document instead.

Exit codes are stable for automation: `0` is a valid non-provider-error
response, `1` is configuration/client failure, `2` is invalid CLI usage from
Clap, and `3` is a structurally valid SCM `provider_error` envelope.

The deprecated query-token event stream is intentionally not supported.

Additional typed commands are available for service health, provider status,
supplier detail, exact supplier-part-number lookup, and SPN batches:

```text
scm health
scm providers
scm detail LCSC C2040
scm spn LCSC C2040
scm batch LCSC C2040 C2870085
```

Use `SCM_CA_BUNDLE` or `--ca-bundle` only for a reviewed private PEM root. The
CLI inherits the Rust client's HTTPS, redirect, timeout, response-size, proxy,
and credential protections. Never place `SCM_TOKEN` in a command argument.
