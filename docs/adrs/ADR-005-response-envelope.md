# ADR-005: API Response Envelope

## Status

Proposed

## Context

The service needs to return more than raw part data. Clients need to know:

- Did the provider succeed or fail?
- Was the response cached?
- How long did the provider take?
- When was the response generated?

This metadata is especially important for lib_cruncher which uses timing data, and
for debugging provider issues.

## Decision

All API responses are wrapped in an envelope:

```json
{
    "status": "ok",
    "supplier": "JLCPCB",
    "provider_latency_ms": 342,
    "service_timestamp": "2026-03-25T14:30:00Z",
    "cached": false,
    "data": { ... }
}
```

### Envelope fields

| Field | Type | Description |
|---|---|---|
| `status` | string | `"ok"`, `"not_found"`, `"provider_error"` |
| `supplier` | string | Provider name |
| `provider_latency_ms` | int | Time spent calling the upstream provider |
| `service_timestamp` | string | ISO 8601 UTC timestamp of this response |
| `cached` | bool | Whether this came from cache (always `false` in v1) |
| `data` | object or list | The part data (single object for detail, list for search) |
| `error` | string or null | Error message when status is not `"ok"` |

### Status values

- `"ok"` — provider returned data successfully
- `"not_found"` — provider returned no results (not an error)
- `"provider_error"` — provider failed (timeout, auth issue, etc.)

### Search responses

For search, `data` is a list:

```json
{
    "status": "ok",
    "supplier": "JLCPCB",
    "provider_latency_ms": 1200,
    "service_timestamp": "...",
    "cached": false,
    "data": [
        { "supplier_part_number": "C2870085", ... },
        { "supplier_part_number": "C12345", ... }
    ]
}
```

### Detail responses

For detail, `data` is a single object:

```json
{
    "status": "ok",
    "supplier": "JLCPCB",
    "provider_latency_ms": 800,
    "service_timestamp": "...",
    "cached": false,
    "data": { "supplier_part_number": "C2870085", ... }
}
```

### `extra_data` handling

`extra_data` from `SupplierPartInfo` is excluded from the default response. Clients
can request it with `?include_raw=true` query parameter. This avoids bloating
responses with full vendor API payloads (Digikey in particular stores the entire
response in `extra_data`).

## Consequences

- Clients always know if a request succeeded and why it failed
- Timing data available from day one for lib_cruncher
- `cached` field is present but always `false` until cache is added
- `extra_data` opt-in prevents bloated responses
