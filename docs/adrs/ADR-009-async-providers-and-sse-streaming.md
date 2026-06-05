# ADR-009: Provider Fan-Out and SSE Streaming

## Status

Accepted.

## Decision

The service exposes an SSE endpoint for browser clients that need incremental
multi-supplier search results:

```text
GET /v1/search/stream?mpn=...&max_results=...
```

Each supplier result is emitted as a complete `ServiceEnvelope` JSON event. The
stream ends with:

```json
{"done": true}
```

The service enforces minimum query length and per-provider result limits for
streamed searches.

## Policy

Synchronous provider calls may be isolated with executor-based fan-out. Provider
adapters can move to native async HTTP when that removes real complexity, but
the public contract remains the same.

## Consequences

- Browser clients can render fast supplier results before slow suppliers finish.
- Broad queries are bounded by `max_results`.
- Single-provider `/v1/search` remains the stable non-streaming endpoint.
