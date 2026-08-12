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
- `error_detail`: optional sanitized machine-readable failure context with a
  stable code, retryability, upstream HTTP status, and upstream request ID
- `rate_limit`: optional provider rate-limit metadata

Search responses use a list in `data`. Detail responses use a single object or
`None`.

## Policy

`extra_data` is excluded by default and included only when callers request
`include_raw=true`.

An upstream authentication, transport, rate-limit, or response-processing
failure MUST use `provider_error`; it MUST NOT be converted to `not_found`.
Diagnostic fields must not contain credentials or unrestricted upstream
response bodies.

## Consequences

- Clients can handle success, miss, and provider failure uniformly.
- Clients can use structured diagnostics without parsing provider-specific
  message text.
- Timing and cache metadata are available without changing the part contract.
- Raw vendor payloads do not bloat normal API responses.
