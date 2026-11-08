# ADR-013: JLC Private Inventory Reads

## Status

Accepted.

## Decision

SCM exposes read-only JLC My Parts Lib inventory at `/v1/account/inventory`
and exact C-code or MPN matches at `/v1/account/inventory/lookup`. Both use the
existing SCM bearer token and JLC credentials from `scm.server.settings`.
`/v1/account/capabilities` reports whether JLC credentials are configured.

Each request scans JLC's private library once, within 100 pages, 25 seconds,
and a bounded response size. JLC repeats its final full page; SCM stops on
that immediate repeat or on a short page. An interrupted scan fails rather
than returning a partial or falsely empty result. The four JLC source counts
remain separate nullable integers; zero and unknown have different meanings.
Each row's `observed_at` records when its page was fetched; the response's
`observed_at` records scan completion. They may differ during a long scan.

## Consequences

- Callers receive one complete observed list or an error, without paging state.
- The list is a live observation across pages, not a supplier snapshot.
- Existing SCM token holders can read account inventory. Purchase history and
  other suppliers require a separate decision.
