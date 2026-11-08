# supply-chain-monkey-contracts

Generated Supply Chain Monkey v1 wire models and a strict, bounded JSON codec.

The checked-in Rust types and package-local JSON Schema resources are generated
from the repository's TypeSpec authority. Consumers should use the public model
types together with `decode` and `encode`; schema resources are implementation
details used to enforce the wire contract at runtime.

```rust
use scm_contracts::{ContractRoot, HealthResponse, decode};

let health: HealthResponse = decode(
    ContractRoot::HealthResponse,
    br#"{"status":"ok"}"#,
    1024,
)?;
assert_eq!(health.status.to_string(), "ok");
# Ok::<(), scm_contracts::CodecError>(())
```

`decode` rejects oversized bodies, invalid UTF-8, duplicate object members,
non-I-JSON values, schema violations, and generated-model conversion failures.
`encode` validates the generated model against the same unmodified root schema.

## Serde JSON feature compatibility

If another dependency enables `serde_json/arbitrary_precision`, enable this
crate's `serde-json-arbitrary-precision` feature too. It recognizes serde's
internal number representation while preserving the SCM wire schemas. Integers
must remain in the exact I-JSON range `-(2^53 - 1)` through `2^53 - 1`;
finite decimals and exponents use binary64 semantics. The feature also rejects
authored object keys named `$serde_json::private::Number` to prevent confusion
with serde's internal representation. Body, duplicate-key, and schema checks
still apply. The feature-off codec retains its existing wide-integer fallback.

This crate contains no HTTP transport, credentials, provider logic, or retry
policy. Use `supply-chain-monkey-client` for service access. Never edit
`src/generated` or `schema` directly; run the repository TypeSpec and
`scm-codegen` commands instead.
