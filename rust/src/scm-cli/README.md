# scm

Small command-line proof for the public async Supply Chain Monkey Rust client.

Set `SCM_URL` or pass `--url`. Authenticated commands read the bearer token
only from `SCM_TOKEN`; there is intentionally no token command-line option.
Use `--json` for the complete typed envelope or the default stable summary for
interactive checks.

Exit codes are stable for automation: `0` is a valid non-provider-error
response, `1` is configuration/client failure, `2` is invalid CLI usage from
Clap, and `3` is a structurally valid SCM `provider_error` envelope.

The deprecated query-token event stream is intentionally not supported.
