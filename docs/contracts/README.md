# Supply Chain Monkey contracts

SCM owns its public HTTP and JSON structure in
`src/tsp/scm/v1/main.tsp`. Deterministic generation emits:

- OpenAPI 3.1 and JSON Schema under `contracts/scm/v1/generated`;
- supported Python models under `src/py/scm/generated/v1`, re-exported by
  `scm.models`; and
- Rust models and schema resources in `rust/src/scm-contracts`.

The TypeSpec-generated OpenAPI is structural authority. FastAPI's runtime
`/openapi.json` is the interactive projection served to Swagger and ReDoc.
[API exploration](../guides/API_EXPLORATION.md) explains both views and their
parity tests.

Python consumers install `supply-chain-monkey[client]`, import
`scm.client.SCMClient`, and use supported names from `scm.models`. Rust
consumers use the separately versioned `supply-chain-monkey-client`; see its
[client guide](../../rust/src/scm-client/README.md).

Consumer applications must not import `scm.server.providers`. Provider
credentials, upstream transports, fallback logic, and supplier-specific policy
remain server-owned and come only from process environment.

Regenerate rather than editing projections:

```powershell
npm run generate:contracts
npm run generate:python
Push-Location rust
cargo run -p scm-codegen --locked
Pop-Location
```

Normal verification uses the corresponding `check:*` commands and
`cargo run -p scm-codegen --locked -- --check`.
