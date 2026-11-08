+++
type = "plan"
id = "scm-jlc-private-inventory-and-rust-bridge"
status = "active"
created = "2026-11-07"

[[steps]]
id = "work"
title = "Reconcile the Rust arbitrary-precision bridge onto the SCM integration base"
status = "done"

[[steps]]
id = "inventory-contract"
title = "Author the focused JLC account-inventory contract and regenerate projections"
status = "done"
depends_on = ["work"]

[[steps]]
id = "jlc-stock-adapter"
title = "Implement bounded signed JLC private-stock scans and exact lookup"
status = "done"
depends_on = ["inventory-contract"]

[[steps]]
id = "account-http-auth"
title = "Expose read-only inventory routes with existing SCM authentication"
status = "done"
depends_on = ["jlc-stock-adapter"]

[[steps]]
id = "clients-cli"
title = "Add typed Python and Rust client access and inventory CLI commands"
status = "done"
depends_on = ["account-http-auth"]

[[steps]]
id = "alx-compatibility"
title = "Prove existing ALX SCM calls and Rust feature graph remain compatible"
status = "pending"
depends_on = ["clients-cli"]

[[steps]]
id = "design-doc-intent-audit"
title = "Audit design docs, ADRs, and requirements against implementation"
status = "pending"
depends_on = ["alx-compatibility"]

[[steps]]
id = "test-runtime-impact-audit"
title = "Audit new test runtime impact"
status = "pending"
depends_on = ["alx-compatibility"]

[[steps]]
id = "external-review"
title = "Obtain independent external review"
status = "pending"
depends_on = ["alx-compatibility", "design-doc-intent-audit", "test-runtime-impact-audit"]

[[steps]]
id = "exact-source-signoff"
title = "Run complete contract, Python, Rust, packaging, and ALX signoff"
status = "pending"
depends_on = ["external-review"]

[[steps]]
id = "integrate-dev"
title = "Integrate the signed candidate through dev after resolving the missing branch"
status = "pending"
depends_on = ["exact-source-signoff"]

[[steps]]
id = "production-pr"
title = "Prepare a production PR only from the signed dev tree"
status = "pending"
depends_on = ["integrate-dev"]

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
id = "rust-feature-bridge"
title = "SCM Rust client supports ALX's arbitrary-precision feature graph without changing existing wire contracts"
status = "pending"

[[exit_criteria]]
id = "private-inventory"
title = "JLC My Parts Lib listing and lookup preserve all four balances and terminate safely"
status = "pending"

[[exit_criteria]]
id = "account-access"
title = "Account routes require SCM authentication and expose no secret or unbounded provider data"
status = "pending"

[[exit_criteria]]
id = "alx-compatibility"
title = "ALX's pinned client and search behavior remain valid against the additive SCM release"
status = "pending"

[[exit_criteria]]
id = "integration-gate"
title = "The exact signed source is integrated through dev before a production PR"
status = "pending"
+++

# JLC My Parts Lib inventory API and Rust client compatibility

## Outcome

Let an authorized SCM caller list and look up the parts in the JLC account's
My Parts Lib, including pre-ordered parts held at JLC, without exposing JLC
credentials. Preserve the existing supplier search and the ALX Rust consumer.
The first release covers account-visible stock, not purchase transactions.

## Starting evidence and decisions

- The [account-data research](../../../research/2026-11-02-account-data-api-review.md)
  records successful signed access to `getPrivateComponentLibrary` with local
  environment credentials. Its response has `componentCode`, `componentModel`,
  and separate `jlcpcbParts`, `globalSourcingParts`, `consignedParts`, and
  `idleStock` balances. It has no total or next-page marker. A request beyond
  the last stock page repeats that final page; zero-balance library rows and
  multiple C-codes for one model were observed.
- The [account-data proposal](../../../scm/design/account-data-api-proposal.md)
  is the design input. This plan implements only account capabilities,
  inventory list, and inventory lookup. PCB/parts order history, files,
  ordering, other suppliers, and physical stock in our own locations are later
  work.
- ALX pins SCM Rust client commit `f48cc2d` with
  `serde-json-arbitrary-precision`. That opt-in codec bridge is present only on
  `origin/fix/scm-serde-json-feature-bridge-20261021`; current `production`
  lacks it. Port the reviewed `f48cc2d` change and its tests onto the current
  SCM integration base. Do not merge the entire divergent fix branch or lose
  later security/dependency changes.
- `origin/dev` is absent as of plan creation. Before integration, fetch and
  review remote branch state, then establish or recover `dev` from the current
  production baseline under the repository's branch policy. Do not use
  `production` as a development branch.
- The pinned `wn-dev-std` plan audit passes at `2026.8.12`. The baseline
  documentation-link audit separately reports an existing missing ADR-010
  target in `docs/adrs/README.md`; resolve that documentation defect before
  claiming a clean documentation signoff.

## Implementation boundary

1. Keep the opt-in Rust codec feature and its numeric, duplicate-member, and
   reserved-key tests. Prove the default feature-off codec still behaves as
   before. Keep the ALX-required feature name available on the new SCM Rust
   client revision.
2. Author the three new read-only `/v1/account` operations in TypeSpec first:
   capabilities, bounded inventory list, and exact SPN/MPN lookup. Generate
   OpenAPI, schemas, Python models/resources, and Rust models through the
   repository tooling. Keep existing `/v1/search`, `/v1/health`, and
   `/v1/providers/status` request and response contracts unchanged.
3. Normalize JLC rows as account-visible records with C-code identity,
   reported model/MPN, observation time, and four separately named balances.
   Preserve null versus zero. Do not sum buckets, substitute public catalog
   stock, or claim a quantity is available to build. A known pre-order C-code
   and My Parts Lib screen comparison can refine labels later; it does not
   block exposing clearly named source balances.
4. Scan the signed JLC API on the server with a bounded page size, request
   count, duration, and response size. Stop after a short page or an immediately
   repeated final page without returning duplicate rows; reject malformed or
   duplicate records. An MPN may match multiple C-codes. A completed live scan
   without a match reports `not_observed`, not proven zero. An incomplete scan
   returns an upstream error, never an empty successful result.
5. Read JLC credentials only from process environment through
   `scm.server.settings`. Reuse the existing `SCM_SERVICE_TOKEN` and authentication
   dependency for account inventory. Do not add another token or cursor key.
   Never log or echo secrets,
   raw stock rows, unbounded provider JSON, addresses, or payment data.
6. Extend the Python and Rust HTTP clients and the Rust `scm` CLI with inventory
   list/lookup. The CLI reads the existing token from `SCM_TOKEN` in
   the process environment, supports JSON output, and exits nonzero on incomplete
   results. Extend the existing local test
   CLI or add a focused safe smoke command without putting tokens in command
   arguments. ALX itself needs no new inventory UI in this slice.

## Verification and compatibility

- Use authored, redacted fixtures for full and short pages, repeated final
  pages, malformed/duplicate records, zero and null balances, duplicate MPNs,
  upstream failures, auth failures, invalid lookup input, and scan bounds. Never
  commit live account responses. Live supplier checks stay opt-in.
- Prove the old ALX-pinned Rust client still decodes existing search, health,
  and provider-status responses from the candidate service. Run ALX's focused
  SCM client and supplier-search tests, and compile the new SCM Rust client in
  ALX's `serde_json/arbitrary_precision` feature graph. ALX's existing
  `stock_quantity` remains supplier catalog stock; private balances exist
  only on new account operations.
- Run TypeSpec and generated-artifact freshness checks, Python pytest, Rust
  locked format/check/Clippy/tests/doctests/rustdoc, Rust dependency policy,
  `uv run rack run L99_signoff`, sdist/wheel build, and Twine check. Update
  operator/client docs and review test runtime impact. Require independent
  review and complete signoff on the exact candidate tree before a PR to
  `production`.

## Integration and release guard

Integrate through `dev` after confirming the remote state. If integration
changes the signed tree, repeat signoff on that tree. Keep Appliku on the
managed `python-3.13-uv` image and `[tool.uv] package = false`; make no
Dockerfile deployment change. A production PR and deployment are later
release actions after this plan's signoff and review gates. Record the commit
and tree IDs, a release version decision for the Python service and Rust
crates, and dev-std logs for each completed work slice.
