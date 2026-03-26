# ADR-009: Async Providers and SSE Streaming

## Status

Proposed

## Context

Provider calls use synchronous `requests.get` which blocks the FastAPI event
loop. A single slow search (e.g., partial MPN "W25Q16" triggering 44 sequential
scraper verifications over 90 seconds) blocks the entire server — no other
requests can be served.

Additionally, the HTTP request/response model gives clients no visibility into
search progress. They wait in the dark until all providers finish or the request
times out.

## Decision

### 1. Async provider HTTP calls

Replace `requests` with `httpx.AsyncClient` in provider code that makes external
HTTP calls (scrapers, vendor APIs). Provider `search_by_mpn` and
`get_part_details` become async methods. This prevents blocking the event loop.

For the initial implementation, wrapping sync provider calls in
`asyncio.run_in_executor()` is acceptable as a stepping stone.

### 2. Result limits and timeouts

Add `max_results` parameter to search endpoints (default 10). Providers stop
after finding this many results. This prevents the scraper from verifying 44+
parts for broad queries.

Add a per-provider timeout (default 15 seconds). If a provider hasn't returned
within the timeout, return whatever results were found and mark status as
`"partial"`.

### 3. SSE streaming endpoint

Add `GET /v1/search/stream?mpn=X&max_results=N` that streams results via
Server-Sent Events. Each provider's results are pushed as a separate SSE event
the moment they complete. The stream ends with a `{"done": true}` event.

Auth is handled via query parameter (`token=X`) since SSE/fetch streaming
supports custom headers via the fetch API but not via EventSource.

The existing `GET /v1/search?supplier=X&mpn=Y` endpoint remains for
single-provider synchronous requests. The streaming endpoint handles the
multi-provider parallel case.

### 4. Minimum query length

Enforce a minimum MPN length of 3 characters at the API level. Queries shorter
than 3 characters return an error immediately.

## SSE Event Format

```
data: {"supplier": "LCSC", "status": "ok", "provider_latency_ms": 280, ...}

data: {"supplier": "Mouser", "status": "ok", "provider_latency_ms": 450, ...}

data: {"supplier": "Digikey", "status": "ok", "provider_latency_ms": 1200, ...}

data: {"supplier": "JLCPCB", "status": "partial", "provider_latency_ms": 15000, ...}

data: {"done": true}
```

Each event is a complete `ServiceEnvelope` JSON object.

## Consequences

- Server can handle concurrent requests even when one search is slow
- Clients see results from fast providers immediately
- Broad queries are bounded by max_results and timeout
- Short garbage queries are rejected
- The existing single-provider endpoint is unchanged
- Client library needs a streaming option for search_all
