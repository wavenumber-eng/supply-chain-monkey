import "@typespec/http";
import "@typespec/json-schema";
import "@typespec/openapi";

using TypeSpec.Http;
using TypeSpec.JsonSchema;

@service(#{ title: "supply-chain-monkey" })
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
  text: string,
  number: numeric,
  boolean: boolean,
  nullValue: null,
  array: JsonValue[],
  object: Record<JsonValue>,
}

/** The one reviewed provider-owned flexible JSON object. */
@extension("x-wn-flexible", true)
@extension(
  "x-wn-flexible-reason",
  "Raw provider data is returned only when include_raw is explicitly requested."
)
model ProviderRawData is Record<JsonValue>;

enum Supplier {
  JLCPCB: "JLCPCB",
  LCSC: "LCSC",
  Digikey: "Digikey",
  Mouser: "Mouser",
}

enum EnvelopeStatus {
  ok: "ok",
  partial: "partial",
  notFound: "not_found",
  providerError: "provider_error",
}

enum BatchItemStatus {
  ok: "ok",
  notFound: "not_found",
  providerError: "provider_error",
}

model PriceBreak {
  qty: JsonInteger;
  unit_price: float64;
  currency: string;
}

model Part {
  supplier: string;
  source_provider: string;
  supplier_part_number: string;
  manufacturer: string;
  manufacturer_part_number: string;
  description: string;
  datasheet_url: string;
  product_url: string;
  stock_quantity: JsonInteger;
  stock_status: string;
  price_breaks: PriceBreak[];
  lifecycle_status: string;
  packaging: string;
  extra_data: ProviderRawData | null;
}

model RateLimitSnapshot {
  request_limit: JsonInteger | null;
  requests_remaining: JsonInteger | null;
  burst_limit: JsonInteger | null;
  burst_remaining: JsonInteger | null;
  reset_seconds: JsonInteger | null;
  reset_time: string | null;
  retry_after_seconds: JsonInteger | null;
  observed_at: Rfc3339Timestamp;
}

model SupplierCapabilities {
  supplier: string;
  provider_kind: string;
  supports_mpn_search: boolean;
  supports_keyword_search: boolean;
  supports_spn_lookup: boolean;
  supports_native_spn_batch: boolean;
  max_spn_batch_size: JsonInteger;
  min_request_interval_seconds: float64;
  rate_limit_per_minute: JsonInteger | null;
  rate_limit_per_day: JsonInteger | null;
  usage_unit: string;
  supports_quota_headers: boolean;
  notes: string[];
}

model ServiceErrorDetail {
  code: string;
  retryable: boolean;
  upstream_status_code: int32 | null;
  upstream_request_id: string | null;
}

model EnvelopeMetadata {
  status: EnvelopeStatus;
  supplier: string;
  parameter_field_name: string;
  provider_latency_ms: JsonInteger;
  provider_capabilities: SupplierCapabilities | null;
  rate_limit: RateLimitSnapshot | null;
  service_timestamp: Rfc3339Timestamp;
  cached: boolean;
  error: string | null;
  error_detail: ServiceErrorDetail | null;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.search-envelope")
model SearchEnvelope extends EnvelopeMetadata {
  data: Part[] | null;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.detail-envelope")
model DetailEnvelope extends EnvelopeMetadata {
  data: Part | null;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-envelope")
model SpnEnvelope extends EnvelopeMetadata {
  data: Part | null;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-batch-request")
model SpnBatchRequest {
  supplier: string;
  @minItems(1)
  @maxItems(1000)
  spns: string[];
  include_raw?: boolean = false;
}

model SpnBatchItem {
  spn: string;
  status: BatchItemStatus;
  part: Part | null;
  error: string | null;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.spn-batch-envelope")
model SpnBatchEnvelope extends EnvelopeMetadata {
  data: SpnBatchItem[] | null;
}

model ProviderStatusEntry {
  configured: boolean;
  backend?: string;
  capabilities: SupplierCapabilities;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.provider-status-response")
model ProviderStatusResponse {
  providers: Record<ProviderStatusEntry>;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.health-response")
model HealthResponse {
  status: "ok";
}

model HttpErrorDetail {
  detail: string;
}

model ValidationErrorItem {
  loc: (string | JsonInteger)[];
  msg: string;
  type: string;
  input?: JsonValue;
  ctx?: Record<JsonValue>;
}

model ValidationErrorDetail {
  detail: ValidationErrorItem[];
}

@error
model UnauthorizedResponse {
  @statusCode status_code: 401;
  @body body: HttpErrorDetail;
}

@error
model BadRequestResponse {
  @statusCode status_code: 400;
  @body body: HttpErrorDetail;
}

@error
model ValidationErrorResponse {
  @statusCode status_code: 422;
  @body body: ValidationErrorDetail;
}

@error
model ServerConfigurationErrorResponse {
  @statusCode status_code: 500;
  @body body: HttpErrorDetail;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.stream-done-event")
model StreamDoneEvent {
  done: true;
}

@jsonSchema
@id("urn:supply-chain-monkey:schema:v1.stream-search-event")
union StreamSearchEvent {
  result: SearchEnvelope,
  done: StreamDoneEvent,
}

model EventStreamResponse {
  @statusCode status_code: 200;
  @header("Content-Type") content_type: "text/event-stream";
  @header("Cache-Control") cache_control: "no-cache";
  @header("X-Accel-Buffering") accelerator_buffering: "no";
  @body body: string;
}

@route("/v1")
interface PublicOperations {
  @get
  @route("/health")
  health(): HealthResponse;

  @get
  @route("/")
  statusPage(): {
    @statusCode status_code: 200;
    @header content_type: "text/html";
    @body body: string;
  };
}

@useAuth(BearerAuth)
@route("/v1")
interface AuthenticatedOperations {
  @get
  @route("/providers/status")
  providersStatus():
    | ProviderStatusResponse
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  @get
  @route("/search")
  search(
    @query supplier: string,
    @query mpn: string,
    @query include_raw?: boolean = false,
    @query max_results?: QueryInteger = 10,
  ):
    | SearchEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  @get
  @route("/detail")
  detail(
    @query supplier: string,
    @query part: string,
    @query include_raw?: boolean = false,
  ):
    | DetailEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  @get
  @route("/spn")
  spn(
    @query supplier: string,
    @query spn: string,
    @query include_raw?: boolean = false,
  ):
    | SpnEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;

  @post
  @route("/spn/batch")
  spnBatch(@body request: SpnBatchRequest):
    | SpnBatchEnvelope
    | UnauthorizedResponse
    | ValidationErrorResponse
    | ServerConfigurationErrorResponse;
}

@useAuth(ApiKeyAuth<ApiKeyLocation.query, "token">)
@route("/v1")
interface LegacyStreamingOperations {
  #deprecated "Legacy query-token SSE surface; excluded from new clients."
  @TypeSpec.OpenAPI.extension("x-scm-event-roots", #["StreamSearchEvent"])
  @get
  @route("/search/stream")
  searchStream(
    @query mpn: StreamMpn,
    @query max_results?: QueryInteger = 10,
    @query timeout?: float64 = 15.0,
    @query include_raw?: boolean = false,
    @query suppliers?: string = "",
  ):
    | EventStreamResponse
    | BadRequestResponse
    | UnauthorizedResponse
    | ValidationErrorResponse;
}
