+++
type = "adr"
id = "scm-adr-0013"
domain = "scm"
status = "accepted"
title = "TypeSpec wire authority and generated Rust client boundary"
created = "2026-08-31"
plan_refs = ["scm-rust-client-typespec"]
adr_refs = ["ADR-005", "ADR-008", "ADR-009"]
implementation_refs = [
  { kind = "local_file", target = "src/py/scm/models.py" },
  { kind = "local_file", target = "src/py/scm/client.py" },
  { kind = "local_file", target = "src/py/scm/server/routers" },
]
+++

# TypeSpec wire authority and generated Rust client boundary

## Context

Supply Chain Monkey currently defines its public data shapes as handwritten
Pydantic models in `scm.models`. FastAPI handlers return `ServiceEnvelope`, but
most handlers do not declare endpoint-specific response models and
`ServiceEnvelope.data` is untyped. Consequently, the served OpenAPI document
does not express the successful response bodies precisely enough to generate a
strict Rust client.

Alexandria is moving to Rust and needs a stable SCM client boundary. Its
`appz/data_models` TypeSpec work demonstrates a useful structural-authority and
catalog pattern, but its ALX models are not the owner of SCM's service contract.

## Decision

SCM will own the TypeSpec source for its public HTTP and JSON wire contract.
TypeSpec-generated JSON Schema 2020-12, OpenAPI 3.1, and a normalized contract
catalog are the machine-readable structural authority. The catalog identifies
all endpoint request and response roots, schema artifacts, and digests so that
Python and Rust generation do not maintain independent handwritten root lists.

TypeSpec owns field names, types, requiredness, nullability, bounds, closed
object shapes, unions, operation parameters, HTTP methods and paths, and bearer
authentication metadata. Handwritten code continues to own provider behavior,
credentials, transport, concurrency, retry policy, caching, and error policy.

The TypeSpec compiler and emitters are development/release tools only. They do
not enter the Appliku Python runtime. SCM does not depend on Alexandria or a
machine-local `appz/data_models` path at build time or runtime.

The owned locations and identities are:

- TypeSpec namespace: `Wavenumber.SupplyChainMonkey.V1`;
- authored TypeSpec: `src/tsp/scm/v1/` with `main.tsp` as its entry point;
- normalized catalog: `contracts/scm/v1/generated/wn_contract_catalog.a0.json`;
- JSON Schemas: `contracts/scm/v1/generated/schema/`;
- OpenAPI 3.1: `contracts/scm/v1/generated/openapi.json`;
- generated Python internals: `src/py/scm/generated/v1/`, re-exported only
  through the existing supported `scm.models` surface;
- Rust workspace: `rust/`, with generated internals owned by its contracts
  crate; and
- shared wire vectors: `contracts/scm/v1/vectors/` with a digest manifest.

`v1` identifies the deployed URL/wire compatibility family, not a package
version. Service releases retain date versions. The provisional crates.io
package names are `supply-chain-monkey-contracts` and
`supply-chain-monkey-client`; the proof CLI package is
`supply-chain-monkey-cli` and installs the `scm` binary. Registry availability
is rechecked immediately before any separately authorized publication.

## Deployed `/v1` compatibility boundary

The first authority pass describes and tests the deployed `/v1` behavior before
changing it:

- unauthenticated `GET /v1/health` and HTML `GET /v1/`;
- authenticated `GET /v1/providers/status`;
- authenticated `GET /v1/search`, `GET /v1/detail`, and `GET /v1/spn`;
- authenticated `POST /v1/spn/batch`; and
- legacy `GET /v1/search/stream` server-sent events.

Endpoint-specific envelope roots replace the structurally ambiguous `Any` data
slot in generated contracts. The supported Python imports remain
`scm.models.ServiceEnvelope`, `SupplierType`, supplier constants, and
`scm.client.SCMClient`. The implementation may preserve these names through
generated models and handwritten facades, but it must not add alternate import
paths as compatibility shims.

The catalog roots are `HealthResponse`, `ProviderStatusResponse`,
`SearchEnvelope`, `DetailEnvelope`, `SpnEnvelope`, `SpnBatchRequest`,
`SpnBatchEnvelope`, `StreamSearchEvent`, `StreamDoneEvent`, and the explicit
FastAPI-compatible authentication and validation error responses. Shared
declarations include `Supplier`, `EnvelopeStatus`, `Part`, `PriceBreak`,
`SupplierCapabilities`, `RateLimitSnapshot`, `SpnBatchItem`, and
`ServiceErrorDetail`. The catalog, rather than this prose list, becomes root
discovery authority after generation.

The stream's `token` query parameter is an explicitly deprecated compatibility
exception. It is modeled accurately for `/v1` characterization, excluded from
the new Rust client and CLI, and must not be copied into another client. Its
replacement is a separately reviewed, header-authenticated operation or API
version. Until that migration, logs, fixtures, diagnostics, and documentation
must redact the legacy query value.

## Structural codecs

Generated Python and Rust native models are projections, not independent schema
authorities. Both languages use the same strict sequence:

1. enforce the endpoint's response-size bound;
2. reject duplicate JSON object members and non-I-JSON values;
3. validate against the selected, unmodified generated root schema; and
4. decode into the generated Pydantic or Serde model.

Encoding validates the native value against the selected unmodified root schema
before returning bytes. Any typify or Pydantic generator projection is
documented and affects native type generation only. The runtime validator never
uses a rewritten projection schema.

One deliberately flexible JSON value may preserve reviewed provider raw data
when `include_raw` is requested. Other public response objects are closed.

## Rust crate and client boundary

The initial release candidate uses a Cargo workspace with:

- a publishable contracts crate containing generated structural types and the
  strict codec;
- a publishable async client crate containing HTTP behavior; and
- an unpublished generation tool.

Combining the public crates requires a documented review showing that doing so
does not couple contract generation to transport behavior. The public client is
async-first and uses Tokio/reqwest. Multi-provider search is client-side bounded
concurrency over supported single-provider operations. The server's provider
implementations and credentials do not move into Rust.

Transport errors, HTTP errors, contract-validation failures, and SCM
provider-error envelopes remain distinct. Authenticated remote endpoints require
HTTPS, with an explicit loopback-only development/test exception. Redirects are
disabled unless a same-origin, no-downgrade policy is proven. Authorization is
never forwarded cross-origin or included in URLs, errors, `Debug` output,
fixtures, CLI arguments, or logs.

The TLS backend decision is made through cross-platform tests. `rustls` is the
preferred candidate because it avoids an OpenSSL runtime dependency, but it is
accepted only after native/private CA roots and required proxy behavior pass on
Windows, macOS, and Linux. Certificate validation is never disabled.

## Toolchain and audit boundaries

The TypeSpec development boundary pins Node 24.12.0, npm 11.16.0, TypeSpec
compiler/emitters 1.14.0, a private `package.json`, and `package-lock.json`.
Generation and freshness commands are committed and deterministic.

The checked package scripts are `generate:contracts`, `check:typespec`,
`check:contracts`, `generate:python`, and `check:python-generation`; a clean
checkout begins with `npm ci`. JSON Schema and OpenAPI emission use
`@typespec/json-schema` and `@typespec/openapi3`. SCM owns a small catalog
emitter derived from the reviewed Wavenumber pattern in this repository rather
than importing Alexandria by local path.

Python model projection uses `datamodel-code-generator==0.76.0` with the
immutable `practical-py313-20260826` preset, Pydantic v2 output, schema-accurate
nullability, and forbidden extra fields. A catalog-driven wrapper creates the
complete schema input and runs the generator in write or `--check` mode. The official
preview TypeSpec Python client emitter is not used because the supported
handwritten `SCMClient` remains the transport boundary. Runtime validation uses
the Draft 2020-12 validator from `jsonschema` before Pydantic decode; generated
Pydantic validation is an additional native-type gate, not a replacement for
the unmodified schema.

The repository root retains its `python-package` profile under
`wn-dev-std 2026.8.12`. The Rust workspace receives a standalone
`rust/dev-std.toml` with `profile = "rust-app"` and passes:

```text
uvx --from wn-dev-std==2026.8.12 dev-std audit rust --scope repo --scope language
```

This boundary must pass before generated Rust source is accepted.

## Deployment and release boundary

`dev` is a disposable integration branch and has no deployment meaning.
`production` is the authoritative release branch and the only branch coupled to
Appliku. This decision does not change `[tool.uv] package = false`, the managed
`python-3.13-uv` image, `PYTHONPATH` imports, or process-environment credential
ownership through `scm.server.settings`.

This work first produces packaged, hash-bound release candidates and proves an
isolated Alexandria consumer. Publishing crates, releasing the CLI, merging to
`production`, and triggering the production deployment are separately governed
release actions.

## Consequences

- Python, Rust, OpenAPI, and tests share one structural source of truth.
- The first implementation cost includes strict JSON/schema codecs, catalog
  generation, deterministic code generation, and conformance fixtures.
- Public Python compatibility is tested before mechanical server cutover.
- A small Rust CLI can exercise the public client without becoming contract
  authority.
- Winget, Homebrew, and Linux package-channel work remains downstream of a
  proven CLI artifact and does not delay Alexandria's library proof.

## Alternatives considered

- **Generate Rust directly from the current FastAPI OpenAPI.** Rejected because
  successful response bodies are currently underspecified and envelope data is
  `Any`.
- **Put SCM models in Alexandria's `appz/data_models`.** Rejected because it
  reverses service ownership and introduces a cross-repository build boundary.
- **Handwrite matching Rust structs.** Rejected because handwritten Python and
  Rust roots would drift and neither would establish machine-readable wire
  authority.
- **Generate the entire HTTP client.** Deferred because the available TypeSpec
  client emitters do not provide the reviewed Rust behavior, security, and error
  policy required here.
- **Rewrite providers in Rust.** Rejected as unrelated to the Alexandria client
  need and the deployed Python service boundary.

## Implementation promotion gates

Accepting this ADR does not replace a schema, model, handler, client, or package.
The TypeSpec step must prove the recorded route/shape characterization, exact
schema/catalog identities, deterministic commands, and legacy stream boundary.
Runtime cutover follows only after generated Python viability and shared
conformance vectors pass.
