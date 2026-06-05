# ADR-005: API Response Envelope

## Status

Accepted.

## Decision

All supplier API responses use `ServiceEnvelope`.

Envelope fields:

- `status`: `ok`, `not_found`, or `provider_error`
- `supplier`: provider display name
- `provider_latency_ms`: upstream provider duration
- `service_timestamp`: UTC service timestamp
- `cached`: whether the result came from cache
- `data`: part object, list of part objects, or `None`
- `error`: provider/service error text when status is not `ok`
- `rate_limit`: optional provider rate-limit metadata

Search responses use a list in `data`. Detail responses use a single object or
`None`.

## Policy

`extra_data` is excluded by default and included only when callers request
`include_raw=true`.

## Consequences

- Clients can handle success, miss, and provider failure uniformly.
- Timing and cache metadata are available without changing the part contract.
- Raw vendor payloads do not bloat normal API responses.
