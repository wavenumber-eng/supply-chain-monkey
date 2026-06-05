# ADR-007: Parallel Provider Requests

## Status

Accepted.

## Decision

The stable HTTP search/detail endpoint handles one supplier per request:

```text
GET /v1/search?supplier=jlcpcb&mpn=...
GET /v1/detail?supplier=jlcpcb&part=...
```

`SCMClient.search_all()` performs client-side fan-out by issuing one request per
supplier concurrently and returning `{supplier_key: ServiceEnvelope}`.

The server also exposes an SSE stream endpoint for multi-provider progress when
browser clients need incremental results.

## Consequences

- Single-provider response envelopes stay simple and supplier-specific.
- Consumers control which suppliers to query.
- Slow providers do not block fast provider results in client-side fan-out or
  streaming workflows.
