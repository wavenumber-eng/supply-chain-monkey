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

If another dependency enables `serde_json/arbitrary_precision`, explicitly enable
this crate's `serde-json-arbitrary-precision` feature too. Cargo unifies dependency
features; without this handshake, serde's internal number maps are not ordinary
SCM objects and can fail the strict boundary. The feature recognizes those maps
without changing generated schemas or structural models.

With this feature, integer lexemes remain subject to the exact I-JSON range
`-(2^53 - 1)` through `2^53 - 1`, including integers wider than machine integer
types. Decimal and exponent lexemes must be finite binary64 values and are
canonicalized to the same binary64 semantics used by the default codec before
generated-model conversion. Original numeric spelling and arbitrary decimal
precision are not preserved. Duplicate members, body limits and schema validation
remain enforced.

Feature-enabled decoding and encoding reject authored object keys named
`$serde_json::private::Number` at any depth, including escaped spellings on input,
to prevent source objects from impersonating serde's internal numbers. Ordinary
string values containing that text remain valid. This reserved-key guard applies
only with the feature enabled.

Default feature-off behavior is unchanged. It has a pre-existing limitation:
integer tokens wider than `u64`/`i64` can be parsed as finite floating values before
the codec sees their original spelling, bypassing the integer-token range check.
The opt-in bridge checks preserved integer lexemes and does not have that fallback.
This difference does not authorize rejecting otherwise finite decimal/exponent
values merely because their numerical magnitude exceeds the safe integer range.

This crate contains no HTTP transport, credentials, provider logic, or retry
policy. Use `supply-chain-monkey-client` for service access. Never edit
`src/generated` or `schema` directly; run the repository TypeSpec and
`scm-codegen` commands instead.
