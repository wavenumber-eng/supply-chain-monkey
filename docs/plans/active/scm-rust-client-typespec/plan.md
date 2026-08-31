+++
type = "plan"
id = "scm-rust-client-typespec"
status = "active"
created = "2026-08-31"

[[steps]]
id = "work"
title = "Complete implementation and integration signoff"
status = "pending"
depends_on = ["alexandria-consumer-proof", "release-distribution-design"]

[[steps]]
id = "design-doc-intent-audit"
title = "Audit design docs, ADRs, and requirements against implementation"
status = "pending"
depends_on = ["work"]

[[steps]]
id = "test-runtime-impact-audit"
title = "Audit new test runtime impact"
status = "pending"
depends_on = ["work"]

[[steps]]
id = "external-review"
title = "Obtain independent external review"
status = "pending"
depends_on = ["work", "design-doc-intent-audit", "test-runtime-impact-audit"]

[[exit_criteria]]
id = "signoff"
title = "Focused signoff passes"
status = "pending"

[[exit_criteria]]
id = "design-doc-intent-audit"
title = "Design docs, ADRs, and requirements match implementation"
status = "pending"

[[exit_criteria]]
id = "test-runtime-impact-audit"
title = "New tests are listed and runtime impact is reviewed"
status = "pending"

[[exit_criteria]]
id = "external-review"
title = "Independent external review is complete"
status = "pending"

[[steps]]
id = "integration-baseline"
title = "Align dev integration to production and record the clean baseline"
status = "done"

[[steps]]
id = "contract-authority-design"
title = "Approve TypeSpec, versioning, generation, and compatibility boundaries"
status = "done"
depends_on = ["integration-baseline"]

[[steps]]
id = "typespec-v1-contract"
title = "Author the existing v1 HTTP and data contract in TypeSpec"
status = "done"
depends_on = ["contract-authority-design"]

[[steps]]
id = "python-runtime-viability"
title = "Prove generated Python contract and codec viability"
status = "done"
depends_on = ["typespec-v1-contract"]

[[steps]]
id = "python-contract-cutover"
title = "Cut the Python server and client over to generated contract models"
status = "done"
depends_on = ["python-runtime-viability"]

[[steps]]
id = "rust-standard-adoption"
title = "Adopt the wn-dev-std 2026.8.12 Rust application guidance"
status = "done"
depends_on = ["contract-authority-design"]

[[steps]]
id = "rust-contract-generation"
title = "Generate strict Rust contract types from TypeSpec schemas"
status = "done"
depends_on = ["typespec-v1-contract", "rust-standard-adoption"]

[[steps]]
id = "rust-client-library"
title = "Implement the async Rust SCM client library"
status = "done"
depends_on = ["rust-contract-generation"]

[[steps]]
id = "scm-cli-proof"
title = "Build a bounded scm CLI on the Rust client"
status = "done"
depends_on = ["rust-client-library"]

[[steps]]
id = "cross-language-conformance"
title = "Prove Python and Rust conformance against shared vectors"
status = "done"
depends_on = ["python-contract-cutover", "rust-client-library"]

[[steps]]
id = "artifact-candidate-proof"
title = "Prove packaged Python and Rust release candidates in isolation"
status = "active"
depends_on = ["python-contract-cutover", "rust-client-library"]

[[steps]]
id = "alexandria-consumer-proof"
title = "Prove Alexandria can consume the released Rust client boundary"
status = "pending"
depends_on = ["cross-language-conformance", "artifact-candidate-proof"]

[[steps]]
id = "release-distribution-design"
title = "Decide crate, binary, Winget, Homebrew, and Linux release channels"
status = "pending"
depends_on = ["scm-cli-proof", "cross-language-conformance"]
+++

# TypeSpec contracts and Rust SCM client

Establish TypeSpec as the Supply Chain Monkey wire-contract authority, generate strict Rust contract types, produce a publishable async Rust client release candidate for Alexandria, and retain the existing Python service and Appliku deployment boundary.

## Outcomes

- Supply Chain Monkey owns one TypeSpec source for its public `/v1` HTTP and
  JSON contract.
- Python and Rust consume generated structural models derived from that source.
- A publishable, hash-bound async Rust client release candidate exposes the
  supported SCM operations without importing provider implementations or
  credentials. External publication is separately authorized release work.
- Alexandria consumes the exact, hash-bound client candidate through its Rust
  broker boundary before separately governed publication.
- A small `scm` CLI proves the client independently before broader packaging.
- The existing Python service, public Python import surface, provider settings,
  and Appliku deployment mode remain supported.

## Governing Decisions

1. `production` is the authoritative release baseline and the only branch tied
   to Appliku deployment. The disposable `dev` branch is reset to that exact
   commit before work and is integration-only; pushing `dev` cannot be treated
   as deployment evidence.
2. SCM owns its service TypeSpec. The ALX-only TypeSpec authority in
   `appz/data_models` is precedent and reusable design evidence, not a runtime,
   build, or path dependency.
3. TypeSpec owns wire structure: names, requiredness, unions, bounds, closure,
   HTTP operations, authentication metadata, and response shapes. Handwritten
   code owns provider behavior, HTTP execution, concurrency, retries, error
   policy, and credential handling.
4. The first contract pass describes the deployed `/v1` behavior. Breaking
   cleanups require a separately reviewed version rather than being hidden in
   code generation.
5. Generated artifacts are deterministic, checked in, marked generated, and
   protected by regeneration/freshness checks. Language-specific handwritten
   root lists are not contract authority.
6. The Rust library is async-first for Alexandria and CLI use. A blocking API
   is added only if a real consumer requires it.

## Rust Standard Boundary

The implementation must apply the `wn-dev-std 2026.8.12` `rust-app` guidance
without weakening the existing Python-package checks. The
`rust-standard-adoption` step will record the polyglot policy boundary before
source scaffolding. If the installed standard has no composite Python/Rust
profile, use a separately configured Rust audit boundary or add the missing
composite profile upstream; do not relabel the repository `rust-app` and lose
the Python packaging gates.

The Rust boundary must provide:

- a pinned `rust-toolchain.toml`, explicit edition and MSRV, Cargo resolver,
  workspace package metadata, centralized dependencies, and `Cargo.lock`;
- `unsafe_code = "forbid"` and reviewed workspace Clippy lints;
- the canonical Rust hygiene limits: at most 7 arguments, 100 production
  function lines, 150 test function lines, 1,000 file lines, cyclomatic
  complexity 10, and nesting depth 4;
- `cargo fmt --all -- --check`, locked `cargo check`, Clippy with warnings
  denied, locked tests, doctests, and rustdoc with warnings denied;
- dependency/license review, compatibility pruning, and Windows, macOS, and
  Linux CI intent.

The normal reproducible standards invocation is pinned independently of the
developer machine:

```text
uvx --from wn-dev-std==2026.8.12 dev-std audit <path> <scopes>
```

Rack and CI must use that exact release, or install the exact same version from
a committed development lock. The root remains a Python-package policy
boundary. The Rust workspace uses a standalone `rust/dev-std.toml` package
boundary with `standard_version = "2026.8.12"` and `profile = "rust-app"`. Its
exact pinned gate is:

```text
uvx --from wn-dev-std==2026.8.12 dev-std audit rust --scope repo --scope language
```

The `rust-standard-adoption` step must create that boundary and make this exact
command pass before Rust generation begins. A future reviewed composite
workspace profile may replace the two explicit root/subroot audits; it is not
required for this plan.

The repository's unrelated full-audit documentation debt is not silently
claimed green by this plan. Signoff uses explicit passing scopes for repository,
Python, Rust, tests, compatibility, and this plan catalog; any full-audit
failures remain listed as separately governed debt until remediated.

## TLS Decision

`rustls` is a Rust implementation of TLS, the protocol used by HTTPS. It is
not an HTTP client and it does not store or encrypt SCM credentials at rest.
`reqwest` can use it as the HTTPS transport backend instead of the operating
system's native-TLS adapter or an OpenSSL installation.

The client should default to a reviewed rustls configuration if testing shows
that it meets the supported certificate-root and proxy requirements. The
decision must compare:

- rustls with an appropriate native or bundled root-certificate strategy;
- native TLS behavior on supported Windows, macOS, and Linux environments;
- corporate/private certificate authority requirements;
- binary portability, dependency provenance, and release size; and
- explicit failure behavior for invalid certificates and redirects.

No mode may disable certificate validation. New Rust/Python client or CLI code
must never place bearer tokens in URLs, `Debug` output, errors, logs, generated
fixtures, or process arguments. The deployed `/v1/search/stream` query-token
surface is a legacy exception that must be characterized explicitly, marked
deprecated in the authority ADR, excluded from the Rust client, and given a
versioned removal or header-authenticated replacement path.

## Work Steps

### `integration-baseline`

- Reset local and remote `dev` to the exact authoritative `production` commit
  using a lease-protected push.
- Confirm the integration branch contains the expected tree and passes local
  and CI tests. Do not infer or claim an Appliku deployment from `dev`.
- Record the baseline commit, package version, test result, and standard audit
  result. Do not modify `production`.

### `contract-authority-design`

- Add the required ADR before changing structure or API behavior.
- Inventory every route, parameter, response, authentication path, envelope
  status, flexible field, default, and Python public import.
- Decide the TypeSpec namespace, schema identities, contract-version policy,
  generated artifact paths, crate names, and Python generation mechanism.
- Resolve the legacy query-token SSE contradiction: preserve and deprecate it
  as an exact `/v1` compatibility exception excluded from new clients, or
  approve a separately versioned header-authenticated replacement.
- Preserve `[tool.uv] package = false`, the managed `python-3.13-uv` Appliku
  image, provider settings ownership, and the absence of deployment URLs or
  credentials in source.

### `typespec-v1-contract`

- Author closed TypeSpec models for health, provider status, Part results,
  price breaks, rate-limit snapshots, capabilities, service diagnostics, SPN
  batch items, and typed endpoint-specific envelopes.
- Keep provider raw data in one explicitly reviewed flexible JSON field.
- Model request bounds, bearer authentication, HTTP failures, and the current
  streaming surface, including any approved legacy exception, explicitly.
- Emit deterministic JSON Schema and OpenAPI 3.1 artifacts and add compile,
  regeneration, and stale-output gates.
- Emit a machine-readable contract catalog containing schema identities,
  endpoint/request/response roots, artifact paths, and digests. Python and Rust
  generators must discover their complete inventories from this catalog.
- Pin the development-only toolchain with a private `package.json`,
  `package-lock.json`, `packageManager = npm@11.16.0`, Node 24.12.0 policy,
  TypeSpec compiler and emitters at 1.14.0, checked `tspconfig` files, and exact
  `npm ci`, generate, and `--check` commands. None enter the Appliku runtime.
- Capture representative success, not-found, partial, provider-error,
  authentication, validation, and maximum-plus-one vectors.

### `python-runtime-viability`

- Generate Pydantic v2 models and one shared strict structural codec without
  changing server or public-client ownership.
- Decode bounded bytes through duplicate-member and I-JSON preflight, validate
  against the unmodified TypeSpec-generated schema, and only then decode the
  generated model. Encoding must validate against the selected unmodified root
  schema before returning bytes.
- Prove current public symbols and behavior for `ServiceEnvelope`,
  `SupplierType`, supplier constants, and every `SCMClient` method with shared
  vectors before allowing the mechanical cutover.
- Document every generator projection and prove projections affect native type
  generation only, never runtime schema authority.

### `python-contract-cutover`

- Generate Pydantic v2 structural models while keeping `scm.models` the only
  public model import path.
- Make FastAPI routes declare the generated request and response models.
- Keep `scm.client.SCMClient` source compatible for the deployed `/v1`
  contract; do not add alternate compatibility import paths.
- Prove the served OpenAPI/route surface and runtime payloads conform to the
  TypeSpec authority.

### `rust-standard-adoption`

- Establish the Cargo workspace and dev-std Rust audit boundary described
  above.
- Document generated, vendored, unsafe, dependency, and source-root ownership.
- Add the Rust commands to Rack L99 signoff without removing existing Python,
  packaging, or Appliku gates.

### `rust-contract-generation`

- Generate Serde Rust types from the TypeSpec-derived JSON Schemas using a
  deterministic checked-in projection modeled on Alexandria's reviewed
  `typify` work.
- Keep code generation unpublished and keep generated types free of transport
  or provider behavior.
- Reject unknown closed-object members and prove optional/null/default behavior
  with shared vectors.
- Decode bounded bytes through duplicate-member and I-JSON preflight, validate
  against the unmodified generated schema, and then decode the generated Serde
  model. Serde/typify acceptance alone is not contract validation.
- Make catalog discovery authoritative and document every typify projection or
  JSON Schema keyword rewrite.
- Fail `--check` mode for missing, stale, unexpected, or manually edited
  generated files.

### `rust-client-library`

- Produce publishable, clearly named contracts and async client crates, or
  document why one public combined crate is preferable.
- Implement health, provider status, search, detail, SPN, SPN batch, and
  concurrent multi-provider search.
- Keep transport failures, HTTP failures, contract decode failures, and SCM
  provider-error envelopes distinct.
- Apply bounded timeouts and responses, safe URL joining, sensitive bearer
  headers, redirect policy, and the reviewed TLS backend.
- Disable redirects or prove a strict same-origin, no-HTTPS-downgrade policy;
  never forward authorization cross-origin. Require HTTPS for authenticated
  remote endpoints with a narrow explicit loopback test/development exception.
- Prove bounded response bodies, concurrency, cancellation, native/private CA
  behavior, proxy behavior, and absence of tokens from URLs, diagnostics,
  `Debug`, fixtures, and CLI process arguments.
- Use mocked/in-process HTTP tests; live supplier tests remain opt-in.

### `scm-cli-proof`

- Build a small `scm` binary over only the public Rust client.
- Cover health, providers, search, detail, SPN, and batch operations with
  stable human-readable and `--json` output.
- Accept URL/token through explicit configuration without compiled deployment
  values, command-line token echo, or automatic credential-file creation.
- Treat this as a client proof, not yet as acceptance of every package manager.

### `cross-language-conformance`

- Run the same wire vectors through TypeSpec schema validation, generated
  Python models, generated Rust models, the Python client, and the Rust client.
- Prove deterministic field spelling, defaults, nullability, enum handling,
  numeric bounds, flexible raw JSON, and sanitized diagnostics.
- Verify generated artifacts are fresh and generation leaves the worktree
  unchanged.

### `artifact-candidate-proof`

- Run `cargo package --locked` and package-inventory checks for every public
  crate; when crates.io is selected, run `cargo publish --dry-run --locked`.
- Compile an isolated downstream consumer against packaged crate artifacts,
  not workspace or machine-specific paths.
- Build the Python wheel and sdist, install the wheel in a clean environment,
  and verify public imports plus packaged generated schema/catalog resources.
- Bind the exact candidate hashes and versions used by the Alexandria proof.

### `alexandria-consumer-proof`

- Consume a released or exact-candidate Rust client from Alexandria; do not use
  a permanent machine-specific path dependency.
- Keep SCM credentials in the Rust broker and out of browser TypeScript,
  URLs, events, logs, and receipts.
- Prove missing configuration, unreachable service, partial provider failure,
  cancellation, and successful multi-provider search without changing SCM
  provider ownership.

### `release-distribution-design`

- Decide independent versus lockstep crate/service versions and publication
  order.
- Define crates.io and GitHub Release artifacts first.
- Evaluate Winget and Homebrew manifests plus appropriate Linux channels only
  after the CLI artifact, update, rollback, provenance, and cross-platform
  tests are accepted.
- Keep this decision from blocking the initial library and Alexandria proof.

## Nonclaims

- This plan does not rewrite provider adapters in Rust.
- It does not move SCM contracts into `appz/data_models` or Alexandria.
- It does not switch Appliku to Dockerfile builds or install Node/Rust in the
  deployed Python image.
- It does not redesign monetary precision, supplier identifiers, error HTTP
  statuses, or the `/v1` URL space without a separately reviewed version.
- It does not publish packages, reset remote `dev`, or modify Alexandria until
  the corresponding active step is approved and recorded.
- It does not deploy `dev`. Only a reviewed merge into `production` may trigger
  the real Appliku deployment after release signoff.

## Signoff

- `uv run pytest -q`
- `uv run rack run L99_signoff`
- `npm ci`, TypeSpec compile, catalog generation, and deterministic generation
  checks using the pinned toolchain
- Python/TypeSpec/Rust shared contract vectors
- locked Cargo format, check, Clippy, tests, doctests, and rustdoc gates
- a Windows, macOS, and Linux Rust CI matrix with executable TLS, redirect,
  credential-leak, timeout, response-bound, and private-root/proxy tests
- pinned scoped root Python-package audit plus direct Rust `rust-app` policy
  audit; no unqualified full-audit success claim while unrelated debt remains
- Python wheel/sdist build, Twine checks, clean-wheel install proof, Cargo
  package inventory, isolated packaged-crate consumer, and publish dry run
- local and CI L99 Appliku manifest/import checks without a deployment; only
  `production` is deployment-coupled
- design/ADR/requirements intent audit, test-runtime audit, and independent
  external review
