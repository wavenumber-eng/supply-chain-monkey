# SCM `/v1` contract inventory

This inventory records the deployed Python service boundary before TypeSpec
authoring. It is implementation evidence for `scm-adr-0013`; generated catalog
output becomes the machine-readable authority only after that ADR is accepted
and the `typespec-v1-contract` step passes.

## HTTP operations

| Operation root | Method and path | Authentication | Request | Current successful body |
| --- | --- | --- | --- | --- |
| `HealthResponse` | `GET /v1/health` | None | None | `{"status":"ok"}` |
| HTML status page | `GET /v1/` | None | None | `text/html`; excluded from generated clients |
| `ProviderStatusResponse` | `GET /v1/providers/status` | Bearer header | None | Provider-name map with configured/backend/capabilities records |
| `SearchEnvelope` | `GET /v1/search` | Bearer header | `supplier`, `mpn`, optional `include_raw=false`, optional `max_results=10` | `data` is a list of `Part` |
| `DetailEnvelope` | `GET /v1/detail` | Bearer header | `supplier`, `part`, optional `include_raw=false` | `data` is `Part` or null |
| `SpnEnvelope` | `GET /v1/spn` | Bearer header | `supplier`, `spn`, optional `include_raw=false` | `data` is `Part` or null |
| `SpnBatchEnvelope` | `POST /v1/spn/batch` | Bearer header | JSON `SpnBatchRequest` | `data` is a list of `SpnBatchItem` |
| `StreamSearchEvent` | `GET /v1/search/stream` | Deprecated `token` query exception | `mpn`, `token`, optional `max_results=10`, `timeout=15.0`, `include_raw=false`, comma-separated `suppliers` | SSE sequence of `SearchEnvelope`, then `{"done":true}` |

The application root `GET /` redirects to `/v1/` and is excluded from the
public client contract.

## Current validation and status behavior

- Non-stream supplier query values are trimmed and matched case-insensitively;
  responses use canonical values `JLCPCB`, `LCSC`, `Digikey`, and `Mouser`.
- An unknown supplier returns HTTP 200 with a `provider_error` envelope.
- Provider not-found and provider failures also return HTTP 200 envelopes.
- Missing header authentication currently produces FastAPI HTTP 422; malformed
  or incorrect bearer authentication produces HTTP 401; absent server token
  configuration produces HTTP 500.
- Missing or invalid request data produces FastAPI HTTP 422 validation output.
- `SpnBatchRequest.spns` currently has an inclusive item-count bound of 1 to
  1,000 before blank entries are cleaned. Other strings have no declared
  length bound in the non-stream handlers.
- Streaming requires a trimmed MPN length of at least 3 in handwritten logic.
  Its numeric request values currently lack declared upper/lower bounds.
- Non-stream `max_results` currently lacks declared bounds. The TypeSpec v1
  characterization must not invent a deployed constraint; any server hardening
  is reviewed explicitly while the Rust client applies its own safe bounds.
- Stream request errors are HTTP 400/401 JSON details. Once streaming begins,
  provider failures and timeouts are 200-status SSE envelope events.

These irregularities are modeled as compatibility facts, not endorsed as the
shape of a future API version.

## Shared structural declarations

### `Part`

Required wire fields are `supplier`, `source_provider`,
`supplier_part_number`, `manufacturer`, `manufacturer_part_number`,
`description`, `datasheet_url`, `product_url`, `stock_quantity`,
`stock_status`, `price_breaks`, `lifecycle_status`, `packaging`, and
`extra_data`. Existing defaults make all fields appear in normal serialized
responses even where a Python constructor argument is optional.

`PriceBreak` is the normalized closed record `{qty: integer, unit_price:
float64, currency: string}`. `extra_data` is the one deliberately flexible JSON
value and is null unless `include_raw` requests provider-owned data.

### Envelope metadata

All typed envelopes carry:

- `status`: emitted values `ok`, `partial`, `not_found`, or `provider_error`;
- `supplier`;
- `parameter_field_name`;
- `provider_latency_ms`;
- nullable `provider_capabilities` and `rate_limit`;
- `service_timestamp` as an RFC 3339 UTC string;
- `cached`;
- endpoint-specific `data`;
- nullable human-readable `error`; and
- nullable machine-readable `error_detail`.

The deployed handwritten Pydantic model currently accepts arbitrary status
strings and arbitrary `data`. Characterization vectors freeze values actually
emitted by the handlers. The TypeSpec roots close those shapes by endpoint.

### Provider diagnostics

`SupplierCapabilities`, `RateLimitSnapshot`, and `ServiceErrorDetail` retain
their current field names, defaults, and nullability. Provider-status map
entries use `configured`, optional/current `backend`, and `capabilities`.
Provider names remain map keys because changing that deployed body to a list is
not part of v1 characterization.

### SPN batch

`SpnBatchRequest` contains `supplier`, `spns`, and `include_raw`.
`SpnBatchItem` contains `spn`, `status`, nullable `part`, and nullable `error`.
The outer batch status is `ok`, `not_found`, `provider_error`, or `partial`
according to the set of item statuses.

## Catalog and generated ownership

The TypeSpec entry point is `src/tsp/scm/v1/main.tsp` in namespace
`Wavenumber.SupplyChainMonkey.V1`. It emits:

```text
contracts/scm/v1/generated/
  contract_catalog.a0.json
  openapi.json
  schema/
```

The normalized catalog discovers these endpoint roots:

```text
HealthResponse
ProviderStatusResponse
SearchEnvelope
DetailEnvelope
SpnEnvelope
SpnBatchRequest
SpnBatchEnvelope
StreamSearchEvent
StreamDoneEvent
```

Authentication and validation error schemas are operation responses but are not
native-model generation roots unless the catalog marks them as such. Python
generation is owned under `src/py/scm/generated/v1/`; supported imports remain
in `scm.models`. Rust generated internals belong to the contracts crate under
`rust/`. Shared vectors and their digest manifest live under
`contracts/scm/v1/vectors/`.

## Public Python compatibility inventory

The cutover retains:

- `scm.__version__`;
- `scm.models.SupplierType`, `SUPPLIERS`, `PARAMETER_FIELD_NAMES`, and
  `SUPPLIER_LOOKUP`;
- `PartResponse`, `RateLimitSnapshot`, `SupplierCapabilities`,
  `SpnBatchRequest`, `SpnBatchItem`, `ServiceErrorDetail`, and
  `ServiceEnvelope` from `scm.models`; and
- synchronous `SCMClient.health`, `providers_status`, `search`, `search_all`,
  `detail`, `spn`, and `spn_batch` with their current argument names and return
  categories.

The new Rust client does not imply that the supported Python client becomes
async or moves import paths.

## Pre-authoring checks

Before TypeSpec output can claim parity, vectors must cover health, status,
successful/list and nullable-part envelopes, not-found, mixed SPN batch,
provider error, unknown supplier, bearer failures, request validation,
`include_raw`, stream completion, stream timeout, and maximum-plus-one batch
validation. The served OpenAPI is expected to improve only after handlers gain
generated request/response annotations; current empty 200 schemas are evidence,
not generation input.
