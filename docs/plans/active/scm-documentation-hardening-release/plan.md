+++
type = "plan"
id = "scm-documentation-hardening-release"
status = "active"
created = "2026-09-01"

[[steps]]
id = "work"
title = "Harden Rust, TypeSpec, OpenAPI, and navigation documentation"
status = "active"

[[steps]]
id = "documentation-verification"
title = "Prove examples, rustdoc, generated artifacts, and OpenAPI explorers"
status = "pending"
depends_on = ["work"]

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
depends_on = ["documentation-verification", "design-doc-intent-audit", "test-runtime-impact-audit"]

[[steps]]
id = "release-signoff"
title = "Version and sign off the exact 2026.9.1 release candidate"
status = "pending"
depends_on = ["external-review"]

[[steps]]
id = "integrate-dev"
title = "Integrate the signed release candidate into dev"
status = "pending"
depends_on = ["release-signoff"]

[[steps]]
id = "release-production"
title = "Merge the exact signed dev release into production"
status = "pending"
depends_on = ["integrate-dev"]

[[steps]]
id = "deployment-verification"
title = "Verify the production-triggered Appliku deployment"
status = "pending"
depends_on = ["release-production"]

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

[[exit_criteria]]
id = "documentation-coverage"
title = "All supported public Rust APIs and authored TypeSpec declarations have useful human documentation"
status = "pending"

[[exit_criteria]]
id = "openapi-exploration"
title = "A newcomer can run and exercise Swagger, ReDoc, and both OpenAPI documents"
status = "pending"

[[exit_criteria]]
id = "release-2026-9-1"
title = "The exact signed candidate is present on dev and production as release 2026.9.1"
status = "pending"

[[exit_criteria]]
id = "deployment-health"
title = "Appliku reports the production commit deployed and live health/schema smoke checks pass"
status = "pending"
+++

# SCM documentation hardening and 2026.9.1 release

## Outcome

Make the current Rust client, contracts, CLI, TypeSpec authority, generated
OpenAPI, and local/live API exploration straightforward for a new SCM or
Alexandria developer. Release the exact reviewed and signed-off result as SCM
service/Python version `2026.9.1`, integrate it through `dev`, merge that exact
source into deployed branch `production`, and verify the resulting Appliku
deployment.

## Documentation scope

- Add a repository documentation map that distinguishes service operation,
  Python consumption, Rust consumption, contract authoring, generated
  artifacts, and release/deployment material.
- Expand the Rust workspace and crate READMEs with build/run commands, a
  copy-and-paste async client example, builder and environment configuration,
  endpoint examples, `ProviderOutcome` and error handling, concurrent generic
  search, CLI table/JSON behavior, security constraints, and the generated-code
  boundary.
- Document every supported public handwritten Rust API. Enforce missing-doc
  coverage for handwritten public surfaces while explicitly treating generated
  models as projections whose semantic documentation originates in TypeSpec.
  Keep examples compiling through doctests where practical.
- Add useful TypeSpec documentation to every authored service operation,
  request/response root, shared model, enum, scalar, and non-obvious property.
  Include operation summaries and safe representative examples where supported
  so generated OpenAPI, JSON Schema, Rust docs, and Python resources carry the
  same meaning.
- Add one OpenAPI exploration guide covering local test-server startup,
  `SCM_SERVICE_TOKEN`, provider credentials, Swagger `/docs`, ReDoc `/redoc`,
  runtime `/openapi.json`, the canonical generated TypeSpec artifact, bearer
  authorization, unauthenticated health, and the deprecated query-token stream
  warning.
- Explain that TypeSpec-generated OpenAPI is structural authority while the
  FastAPI-served document is the interactive runtime projection. Document how
  parity is tested and how generated artifacts are refreshed and checked.
- Repair stale or incomplete links and examples in the root README,
  contributing documentation, Rust READMEs, contract inventory, and plan index.

## Boundaries

- This slice changes documentation metadata and generated documentation, not
  the deployed `/v1` wire shape, provider behavior, authentication policy,
  Python import surface, or Rust transport behavior.
- Never include company deployment URLs, real bearer tokens, or supplier
  credentials. Examples use loopback or clearly fictional hosts and tokens.
- TypeSpec remains the owned structural authority. Generated OpenAPI, schemas,
  Python resources, catalog, and Rust projections are regenerated by existing
  deterministic tooling and are never hand-edited.
- `2026.9.1` is the SCM service/Python date release. Rust crates retain their
  independently governed SemVer versions unless a separate crate publication
  decision explicitly changes them. No crates.io, Homebrew, or WinGet
  publication is authorized by this plan.
- `dev` is the integration branch and is not tied to deployment. Only merging
  the signed release into `production` is expected to trigger Appliku.

## Verification and review

- Run TypeSpec compilation and all contract, vector, Python-generation, and
  Rust-codegen freshness checks after semantic documentation changes.
- Compile README/client examples or cover them with doctests; run locked Cargo
  format, check, Clippy, workspace tests, doctests, rustdoc with warnings denied,
  cargo-deny, and the pinned wn-dev-std Rust audits.
- Add or retain fast tests proving `/docs`, `/redoc`, and `/openapi.json` are
  reachable and that served schema roots/security match the TypeSpec catalog.
  Inspect the canonical OpenAPI for summaries/descriptions on all supported
  operations and core schemas.
- Run root pytest, Rack L99, Python sdist/wheel build, Twine checks, and the
  packaged Alexandria Rust consumer proof required by the existing release
  boundary.
- Record dev-std logs after the documentation slice, independent review and
  remediation, final exact-source signoff, branch integration, and deployment
  verification. Commit coherent slices as work proceeds.
- Obtain independent review after the documentation/generation slice and again
  if remediation materially changes generated artifacts or enforcement.

## Release and deployment gate

1. Update service/Python version metadata, changelog, and release notes to
   `2026.9.1`; create a clean candidate commit and run the complete signoff on
   that exact commit.
2. Fetch remote state, integrate the exact candidate into `dev` without
   discarding unrelated work, and rerun any checks affected by the integration
   result.
3. Confirm `production` has not advanced unexpectedly. Merge the exact signed
   `dev` release into `production` without force-pushing and push only after all
   gates and independent review are recorded.
4. Verify Appliku identifies the pushed production commit and reaches a healthy
   terminal deployment state. Smoke-test `/v1/health`, `/docs`,
   `/openapi.json`, and one authenticated non-live-provider contract request
   using credentials and deployment URL supplied outside source control.
5. Stop and report rather than retrying blindly if remote branch state,
   deployment identity, credentials, or health cannot be established.
