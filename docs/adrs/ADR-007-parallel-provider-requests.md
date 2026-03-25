# ADR-007: Parallel Provider Requests

## Status

Proposed

## Context

A client searching for a part across multiple suppliers (e.g., JLCPCB + Digikey +
Mouser) should not have to wait for sequential responses. Provider calls are
independent and IO-bound — they should run concurrently.

Two options:

1. **Server-side fan-out**: Client sends one request (e.g., `GET /v1/search?mpn=X`),
   server calls all providers in parallel and returns a combined response.

2. **Client-side parallel requests**: Client sends separate requests per provider
   (e.g., `GET /v1/search?supplier=jlcpcb&mpn=X` and
   `GET /v1/search?supplier=digikey&mpn=X`) concurrently.

## Decision

Use **client-side parallel requests** for v1.

The API requires a `supplier` parameter on search and detail endpoints. Clients
make one request per provider and handle concurrency themselves.

Reasons:

- Simpler server implementation — each request is one provider call
- Client controls which providers to query and how to handle mixed results
- No complex aggregation or partial-failure logic on the server
- Timeouts and retries are per-provider, not combined
- A slow provider doesn't block results from fast providers

A server-side `GET /v1/search/all?mpn=X` fan-out endpoint can be added later if
demand warrants it.

## Consequences

- Each endpoint handles exactly one provider per request
- Clients are responsible for concurrent requests (trivial with async HTTP)
- Response envelope always has a single `supplier` field
- No multi-provider aggregation logic needed in v1
