+++
type = "plan"
id = "scm-cli-multi-provider-table"
status = "active"
created = "2026-08-31"

[[steps]]
id = "work"
title = "Execute plan work"
status = "active"

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
+++

# Multi-provider SCM search and ASCII result table

## Outcome

Make search provider-optional and make interactive search output useful without weakening the existing typed client, security controls, or JSON mode.

## CLI contract

- scm search RT685 searches every provider reported configured by the authenticated provider-status endpoint, using the existing bounded concurrent search_all_with_options client API.
- scm search RT685 --supplier LCSC narrows the search; --supplier is repeatable for explicit multi-provider searches.
- The pre-release positional form search SUPPLIER MPN is replaced rather than retained as an ambiguous compatibility grammar. Help text and README examples must show the new form.
- --json emits one stable multi-provider result document containing each typed envelope or a sanitized per-provider client error. It must never include a bearer token.
- Without --json, successful parts render as a plain ASCII table with columns Supplier, Manufacturer, MPN, Supplier PN, Description, Price, and Stock. Price uses the first price break with its currency and quantity; absent values display a dash.
- Normalize embedded whitespace, truncate long cells deterministically with three ASCII dots, sort rows by stock descending and then supplier/part identity, and keep output safe for redirected or narrow terminals.
- Print concise provider status/error lines after the table for not-found, provider-error, and transport/contract failures. Return 1 for any client failure, otherwise 3 for any provider-error envelope, otherwise 0.

## Boundaries

- Reuse scm-client; do not call providers directly or add the deprecated query-token SSE endpoint to the Rust client.
- SCM_URL and SCM_TOKEN remain the only URL/token inputs and tokens remain absent from arguments, output, diagnostics, and fixtures.
- No crate publication, package-manager work, Alexandria edits, deployment, or production-branch change is part of this plan.

## Verification

- Parser tests cover all-provider, one-provider, repeated-provider, missing-MPN, JSON, and help examples.
- Mock-server tests cover configured-provider discovery, bounded concurrent mixed outcomes, empty configured sets, deterministic tables, truncation/escaping, missing prices, and exit codes.
- Cargo format, check, Clippy, tests, doctests, rustdoc, cargo-deny, root pytest/Rack L99, dev-std audits, runtime-impact audit, and independent review pass.
