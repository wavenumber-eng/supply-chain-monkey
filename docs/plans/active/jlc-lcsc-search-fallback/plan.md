+++
type = "plan"
id = "jlc-lcsc-search-fallback"
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

# Restore LCSC generic search and JLC C-code fallback

## Outcome

Parse LCSC's current third-party generic-search branch when primary inventory search is empty, then use exact/substring-matching shared C-codes as JLCPCB search fallback when JLC's public endpoint fails or returns no usable results.

## Boundaries

Keep requests bounded, preserve genuine not-found behavior, record search provenance, add mocked regression coverage, and verify known live exact and generic searches without changing credentials, deployment, or contracts.
