import "@typespec/http";
import "@typespec/json-schema";
import "@typespec/openapi";

using TypeSpec.Http;
using TypeSpec.JsonSchema;

/**
 * Public HTTP and JSON contract for Supply Chain Monkey v1.
 *
 * SCM normalizes electronic-component data from configured supplier backends.
 * Except for health and the HTML status page, operations require a bearer token.
 */
@service(#{ title: "supply-chain-monkey" })
@TypeSpec.OpenAPI.info(#{ version: "2026.8.12" })
namespace Wavenumber.SupplyChainMonkey.V1;

/** I-JSON interoperable integer range used by SCM JSON payloads. */
@minValue(-9007199254740991)
@maxValue(9007199254740991)
scalar JsonInteger extends safeint;

/** Deployed unbounded integer accepted in HTTP query parsing. */
scalar QueryInteger extends integer;

/** Stream MPN after the deployed handler's trim normalization. */
@minLength(3)
@extension("x-scm-normalization", "trim before minimum-length validation")
scalar StreamMpn extends string;

/** RFC 3339 timestamp retained as the deployed Python string representation. */
@pattern("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$")
scalar Rfc3339Timestamp extends string;

/** JSON-compatible scalar, array, or object value. */
union JsonValue {
  /** JSON string value. */
  text: string,
  /** JSON number value. */
  number: numeric,
  /** JSON boolean value. */
  boolean: boolean,
  /** JSON null value. */
  nullValue: null,
  /** JSON array containing recursively compatible values. */
  array: JsonValue[],
  /** JSON object containing recursively compatible values. */
  object: Record<JsonValue>,
}

/** The one reviewed provider-owned flexible JSON object. */
@extension("x-wn-flexible", true)
@extension(
  "x-wn-flexible-reason",
  "Raw provider data is returned only when include_raw is explicitly requested."
)
model ProviderRawData is Record<JsonValue>;

/** Canonical supplier identifiers emitted by SCM v1. */
enum Supplier {
  /** JLCPCB assembly-parts service. */
  JLCPCB: "JLCPCB",
  /** LCSC component marketplace. */
  LCSC: "LCSC",
  /** DigiKey component distributor. */
  Digikey: "Digikey",
  /** Mouser component distributor. */
  Mouser: "Mouser",
}

/** High-level outcome reported by an SCM response envelope. */
enum EnvelopeStatus {
  /** The provider completed successfully and returned a valid result. */
  ok: "ok",
  /** The provider completed but returned only part of the requested data. */
  partial: "partial",
  /** The provider completed successfully but found no matching part. */
  notFound: "not_found",
  /** The provider could not complete the request. */
  providerError: "provider_error",
}

/** Outcome of one supplier-part-number item in a batch response. */
enum BatchItemStatus {
  /** The item was resolved successfully. */
  ok: "ok",
  /** No matching supplier part was found. */
  notFound: "not_found",
  /** The provider could not resolve the item. */
  providerError: "provider_error",
}

/** One quantity-based unit-price offer normalized from a supplier. */
model PriceBreak {
  /** Minimum order quantity for this unit price. */
  qty: JsonInteger;
  /** Price per component at the associated quantity. */
  unit_price: float64;
  /** Supplier-reported ISO-style currency code. */
  currency: string;
}

/** Normalized electronic-component result returned by supplier operations. */
model Part {
  /** Canonical supplier associated with this result. */
  supplier: string;
  /** Backend that produced the normalized result. */
  source_provider: string;
  /** Supplier-owned ordering or catalog number. */
  supplier_part_number: string;
  /** Component manufacturer name. */
  manufacturer: string;
  /** Manufacturer-owned part number. */
  manufacturer_part_number: string;
  /** Human-readable supplier description. */
  description: string;
  /** Datasheet URL, or an empty string when unavailable. */
  datasheet_url: string;
  /** Supplier product-page URL, or an empty string when unavailable. */
  product_url: string;
  /** Supplier-reported available stock quantity. */
  stock_quantity: JsonInteger;
  /** Human-readable supplier stock status. */
  stock_status: string;
  /** Quantity-based prices in provider order. */
  price_breaks: PriceBreak[];
  /** Supplier-reported lifecycle state. */
  lifecycle_status: string;
  /** Supplier-reported packaging description. */
  packaging: string;
  /** Provider-owned data, present only when explicitly requested. */
  extra_data: ProviderRawData | null;
}

/** Rate-limit information observed on the provider response. */
model RateLimitSnapshot {
  /** Total request quota, when reported. */
  request_limit: JsonInteger | null;
  /** Requests remaining in the current quota window, when reported. */
  requests_remaining: JsonInteger | null;
  /** Burst quota, when reported. */
  burst_limit: JsonInteger | null;
  /** Burst requests remaining, when reported. */
  burst_remaining: JsonInteger | null;
  /** Seconds until the quota resets, when reported. */
  reset_seconds: JsonInteger | null;
  /** Provider-formatted quota reset time, when reported. */
  reset_time: string | null;
  /** Provider-requested retry delay in seconds, when reported. */
  retry_after_seconds: JsonInteger | null;
  /** Time at which SCM observed this rate-limit state. */
  observed_at: Rfc3339Timestamp;
}

/** Search and lookup features exposed by one configured provider backend. */
model SupplierCapabilities {
  /** Canonical supplier represented by the backend. */
  supplier: string;
  /** Implementation category used for provider diagnostics. */
  provider_kind: string;
  /** Whether manufacturer-part-number search is supported. */
  supports_mpn_search: boolean;
  /** Whether general keyword search is supported. */
  supports_keyword_search: boolean;
  /** Whether exact supplier-part-number lookup is supported. */
  supports_spn_lookup: boolean;
  /** Whether the upstream provider has a native batch lookup. */
  supports_native_spn_batch: boolean;
  /** Maximum batch size accepted by SCM for this provider. */
  max_spn_batch_size: JsonInteger;
  /** Minimum delay SCM applies between provider requests. */
  min_request_interval_seconds: float64;
  /** Provider request quota per minute, when known. */
  rate_limit_per_minute: JsonInteger | null;
  /** Provider request quota per day, when known. */
  rate_limit_per_day: JsonInteger | null;
  /** Unit consumed by one reported quota usage event. */
  usage_unit: string;
  /** Whether upstream quota headers are exposed in envelope metadata. */
  supports_quota_headers: boolean;
  /** Human-readable capability and operational notes. */
  notes: string[];
}

/** Sanitized machine-readable context for a provider failure. */
model ServiceErrorDetail {
  /** Stable SCM error category. */
  code: string;
  /** Whether retrying later may succeed. */
  retryable: boolean;
  /** Sanitized upstream HTTP status, when available. */
  upstream_status_code: int32 | null;
  /** Sanitized upstream request identifier, when available. */
  upstream_request_id: string | null;
}

/** Metadata shared by typed SCM operation envelopes. */
model EnvelopeMetadata {
  /** High-level provider outcome. */
  status: EnvelopeStatus;
  /** Canonical or requested supplier name associated with the outcome. */
  supplier: string;
  /** Query parameter name used to identify the requested part. */
  parameter_field_name: string;
  /** Provider execution time measured by SCM in milliseconds. */
  provider_latency_ms: JsonInteger;
  /** Provider features known at request time. */
  provider_capabilities: SupplierCapabilities | null;
  /** Provider rate-limit state observed for this request. */
  rate_limit: RateLimitSnapshot | null;
  /** Time at which SCM produced the response. */
  service_timestamp: Rfc3339Timestamp;
  /** Whether SCM returned a cached provider result. */
  cached: boolean;
  /** Sanitized human-readable error, or null for normal outcomes. */
  error: string | null;
  /** Sanitized structured error details, when available. */
  error_detail: ServiceErrorDetail | null;
}

/** Result envelope for manufacturer-part-number search. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.search-envelope")
model SearchEnvelope extends EnvelopeMetadata {
  /** Matching normalized parts, or null when the provider did not return data. */
  data: Part[] | null;
}

/** Result envelope for supplier detail lookup. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.detail-envelope")
model DetailEnvelope extends EnvelopeMetadata {
  /** Resolved normalized part, or null when unavailable. */
  data: Part | null;
}

/** Result envelope for exact supplier-part-number lookup. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-envelope")
model SpnEnvelope extends EnvelopeMetadata {
  /** Resolved normalized part, or null when unavailable. */
  data: Part | null;
}

/** Request for multiple exact supplier-part-number lookups. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-batch-request")
model SpnBatchRequest {
  /** Supplier whose part numbers should be resolved. */
  supplier: string;
  /** Supplier part numbers to resolve; between one and 1,000 items. */
  @minItems(1)
  @maxItems(1000)
  spns: string[];
  /** Include provider-owned raw data in returned parts. */
  include_raw?: boolean = false;
}

/** Result for one supplier part number in a batch lookup. */
model SpnBatchItem {
  /** Supplier part number from the corresponding request item. */
  spn: string;
  /** Outcome of resolving this item. */
  status: BatchItemStatus;
  /** Resolved normalized part, or null when unavailable. */
  part: Part | null;
  /** Sanitized item-specific error, or null for normal outcomes. */
  error: string | null;
}

/** Result envelope for a batch supplier-part-number lookup. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-batch-envelope")
model SpnBatchEnvelope extends EnvelopeMetadata {
  /** Per-item results, or null when the provider could not process the batch. */
  data: SpnBatchItem[] | null;
}

/** Configuration and capabilities reported for one provider. */
model ProviderStatusEntry {
  /** Whether the provider is currently configured for use. */
  configured: boolean;
  /** Selected backend implementation, when available. */
  backend?: string;
  /** Features and operational limits exposed by the provider. */
  capabilities: SupplierCapabilities;
}

/** Map of provider names to current configuration and capabilities. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.provider-status-response")
model ProviderStatusResponse {
  /** Provider status keyed by canonical provider name. */
  providers: Record<ProviderStatusEntry>;
}

/** Public service health response. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.health-response")
model HealthResponse {
  /** Constant healthy-state marker. */
  status: "ok";
}

/** FastAPI-compatible HTTP error body. */
model HttpErrorDetail {
  /** Human-readable request or server error. */
  detail: string;
}

/** One FastAPI-compatible validation failure. */
model ValidationErrorItem {
  /** Request location of the invalid value. */
  loc: (string | JsonInteger)[];
  /** Human-readable validation message. */
  msg: string;
  /** Stable validation error type. */
  type: string;
  /** Rejected input value, when included by FastAPI. */
  input?: JsonValue;
  /** Additional validation context, when included by FastAPI. */
  ctx?: Record<JsonValue>;
}

/** FastAPI-compatible collection of request validation failures. */
model ValidationErrorDetail {
  /** Individual validation failures. */
  detail: ValidationErrorItem[];
}

/** Response returned when bearer authentication fails. */
@error
model UnauthorizedResponse {
  /** HTTP unauthorized status. */
  @statusCode status_code: 401;
  /** Sanitized authentication failure. */
  @body body: HttpErrorDetail;
}

/** Response returned for a malformed legacy stream request. */
@error
model BadRequestResponse {
  /** HTTP bad-request status. */
  @statusCode status_code: 400;
  /** Sanitized request failure. */
  @body body: HttpErrorDetail;
}

/** Response returned when request validation fails. */
@error
model ValidationErrorResponse {
  /** HTTP unprocessable-content status. */
  @statusCode status_code: 422;
  /** Structured request validation failures. */
  @body body: ValidationErrorDetail;
}

/** Response returned when SCM authentication is not configured. */
@error
model ServerConfigurationErrorResponse {
  /** HTTP internal-server-error status. */
  @statusCode status_code: 500;
  /** Sanitized server configuration failure. */
  @body body: HttpErrorDetail;
}

/** Terminal event emitted after all legacy stream providers complete. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.stream-done-event")
model StreamDoneEvent {
  /** Constant marker identifying the terminal stream event. */
  done: true;
}

/** One result or terminal event from the legacy search stream. */
@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.stream-search-event")
union StreamSearchEvent {
  /** Search result from one provider. */
  result: SearchEnvelope,
  /** Terminal marker after all providers complete. */
  done: StreamDoneEvent,
}

/** HTTP server-sent-event response used by the legacy stream. */
model EventStreamResponse {
  /** HTTP success status. */
  @statusCode status_code: 200;
  /** Server-sent-event media type. */
  @header("Content-Type") content_type: "text/event-stream";
  /** Directive preventing response caching. */
  @header("Cache-Control") cache_control: "no-cache";
  /** Directive disabling reverse-proxy buffering. */
  @header("X-Accel-Buffering") accelerator_buffering: "no";
  /** Serialized server-sent-event byte stream. */
  @body body: string;
}

/** Operations that do not require SCM bearer authentication. */
@route("/v1")
interface PublicOperations {
  /** Return the current service health marker. */
  @summary("Check service health")
  @get
  @route("/health")
  health(): HealthResponse;

  /** Return the human-facing SCM status and demonstration page. */
  @summary("View the SCM status page")
  @get
  @route("/")
  statusPage(): {
    /** HTTP success status. */
    @statusCode status_code: 200;
    /** HTML response media type. */
    @header("Content-Type") content_type: "text/html";
    /** Rendered HTML status page. */
    @body body: string;
  };
}

/** SCM operations authenticated with the `Authorization: Bearer` header. */
@useAuth(BearerAuth)
@route("/v1")
interface AuthenticatedOperations {
  /** Return configuration and capabilities for every known provider. */
  @summary("List provider status and capabilities")
  @get
  @route("/providers/status")
  providersStatus():
    | ProviderStatusResponse
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  /** Search one supplier for a manufacturer part number. */
  @summary("Search a supplier by manufacturer part number")
  @get
  @route("/search")
  search(
    /** Supplier backend to search; matching is case-insensitive. */
    @query supplier: string,
    /** Manufacturer part number or provider-supported search term. */
    @query mpn: string,
    /** Include provider-owned raw data in returned parts. */
    @query include_raw?: boolean = false,
    /** Maximum number of matching parts requested from the provider. */
    @query max_results?: QueryInteger = 10,
  ):
    | SearchEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  /** Resolve supplier detail for a supplier-owned catalog number. */
  @summary("Get supplier part detail")
  @get
  @route("/detail")
  detail(
    /** Supplier backend that owns the catalog number. */
    @query supplier: string,
    /** Supplier-owned part or catalog number. */
    @query part: string,
    /** Include provider-owned raw data in the returned part. */
    @query include_raw?: boolean = false,
  ):
    | DetailEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  /** Resolve one exact supplier part number. */
  @summary("Look up an exact supplier part number")
  @get
  @route("/spn")
  spn(
    /** Supplier backend that owns the part number. */
    @query supplier: string,
    /** Exact supplier-owned part number. */
    @query spn: string,
    /** Include provider-owned raw data in the returned part. */
    @query include_raw?: boolean = false,
  ):
    | SpnEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  /** Resolve multiple exact part numbers from one supplier. */
  @summary("Look up a batch of supplier part numbers")
  @post
  @route("/spn/batch")
  spnBatch(
    /** One supplier and between one and 1,000 supplier part numbers. */
    @body request: SpnBatchRequest,
  ):
    | SpnBatchEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;
}

/**
 * Deprecated v1 query-token compatibility surface. Never place a real service token in this query, Swagger operation, logs, or shared URLs.
 */
model LegacyQueryTokenAuth is ApiKeyAuth<ApiKeyLocation.query, "token">;

/** Deprecated query-token search stream retained only for v1 compatibility. */
@useAuth(LegacyQueryTokenAuth)
@route("/v1")
interface LegacyStreamingOperations {
  /**
   * Stream per-provider searches using the deprecated query-token contract.
   * Never place a real service token in this query, Swagger operation, logs, or shared URLs. New clients must use header-authenticated non-stream operations.
   */
  @summary("Stream legacy multi-provider search results")
  #deprecated "Legacy query-token SSE surface; excluded from new clients."
  @TypeSpec.OpenAPI.extension("x-scm-event-roots", #["StreamSearchEvent"])
  @get
  @route("/search/stream")
  searchStream(
    /** Manufacturer part number after trim normalization. */
    @query mpn: StreamMpn,
    /** Maximum number of results requested from each provider. */
    @query max_results?: QueryInteger = 10,
    /** Per-provider completion timeout in seconds. */
    @query timeout?: float64 = 15.0,
    /** Include provider-owned raw data in returned parts. */
    @query include_raw?: boolean = false,
    /** Comma-separated provider names, or empty for all providers. */
    @query suppliers?: string = "",
  ):
    | EventStreamResponse
    | BadRequestResponse
    | UnauthorizedResponse
    | ValidationErrorResponse;
}
