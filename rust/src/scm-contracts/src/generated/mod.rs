#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod detail_envelope;
pub use detail_envelope::DetailEnvelope;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod health_response;
pub use health_response::HealthResponse;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod provider_status_response;
pub use provider_status_response::ProviderStatusResponse;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod search_envelope;
pub use search_envelope::SearchEnvelope;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod spn_batch_envelope;
pub use spn_batch_envelope::SpnBatchEnvelope;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod spn_batch_request;
pub use spn_batch_request::SpnBatchRequest;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod spn_envelope;
pub use spn_envelope::SpnEnvelope;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod stream_done_event;
pub use stream_done_event::StreamDoneEvent;
#[allow(clippy::derivable_impls, reason = "typify emits explicit defaults")]
#[rustfmt::skip]
mod stream_search_event;
pub use stream_search_event::StreamSearchEvent;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ContractRoot {
    DetailEnvelope,
    HealthResponse,
    ProviderStatusResponse,
    SearchEnvelope,
    SpnBatchEnvelope,
    SpnBatchRequest,
    SpnEnvelope,
    StreamDoneEvent,
    StreamSearchEvent,
}
impl ContractRoot {
    pub const ALL: &'static [Self] = &[
        Self::DetailEnvelope,
        Self::HealthResponse,
        Self::ProviderStatusResponse,
        Self::SearchEnvelope,
        Self::SpnBatchEnvelope,
        Self::SpnBatchRequest,
        Self::SpnEnvelope,
        Self::StreamDoneEvent,
        Self::StreamSearchEvent,
    ];
    pub const fn schema_id(self) -> &'static str {
        match self {
            Self::DetailEnvelope => "urn:supply-chain-monkey:schema:v1.detail-envelope",
            Self::HealthResponse => "urn:supply-chain-monkey:schema:v1.health-response",
            Self::ProviderStatusResponse => {
                "urn:supply-chain-monkey:schema:v1.provider-status-response"
            }
            Self::SearchEnvelope => "urn:supply-chain-monkey:schema:v1.search-envelope",
            Self::SpnBatchEnvelope => {
                "urn:supply-chain-monkey:schema:v1.spn-batch-envelope"
            }
            Self::SpnBatchRequest => {
                "urn:supply-chain-monkey:schema:v1.spn-batch-request"
            }
            Self::SpnEnvelope => "urn:supply-chain-monkey:schema:v1.spn-envelope",
            Self::StreamDoneEvent => {
                "urn:supply-chain-monkey:schema:v1.stream-done-event"
            }
            Self::StreamSearchEvent => {
                "urn:supply-chain-monkey:schema:v1.stream-search-event"
            }
        }
    }
    pub const fn schema(self) -> &'static str {
        match self {
            Self::DetailEnvelope => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/DetailEnvelope.json")
                )
            }
            Self::HealthResponse => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/HealthResponse.json")
                )
            }
            Self::ProviderStatusResponse => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"),
                    "/schema/ProviderStatusResponse.json")
                )
            }
            Self::SearchEnvelope => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SearchEnvelope.json")
                )
            }
            Self::SpnBatchEnvelope => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnBatchEnvelope.json")
                )
            }
            Self::SpnBatchRequest => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnBatchRequest.json")
                )
            }
            Self::SpnEnvelope => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnEnvelope.json")
                )
            }
            Self::StreamDoneEvent => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/StreamDoneEvent.json")
                )
            }
            Self::StreamSearchEvent => {
                include_str!(
                    concat!(env!("CARGO_MANIFEST_DIR"), "/schema/StreamSearchEvent.json")
                )
            }
        }
    }
}
pub(crate) const GENERATED_SCHEMAS: &[(&str, &str)] = &[
    (
        "urn:supply-chain-monkey:schema:v1.declaration.BadRequestResponse",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/BadRequestResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.BatchItemStatus",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/BatchItemStatus.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.EnvelopeMetadata",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/EnvelopeMetadata.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.EnvelopeStatus",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/EnvelopeStatus.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.EventStreamResponse",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/EventStreamResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.HttpErrorDetail",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/HttpErrorDetail.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.JsonInteger",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/JsonInteger.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.JsonValue",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/JsonValue.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.Part",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/Part.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.PriceBreak",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/PriceBreak.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ProviderRawData",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ProviderRawData.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ProviderStatusEntry",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ProviderStatusEntry.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.QueryInteger",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/QueryInteger.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.RateLimitSnapshot",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/RateLimitSnapshot.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.RecordJsonValue",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/RecordJsonValue.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.RecordProviderStatusEntry",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/RecordProviderStatusEntry.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.Rfc3339Timestamp",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/Rfc3339Timestamp.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ServerConfigurationErrorResponse",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"),
            "/schema/ServerConfigurationErrorResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ServiceErrorDetail",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ServiceErrorDetail.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.SpnBatchItem",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnBatchItem.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.StreamMpn",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/StreamMpn.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.Supplier",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/Supplier.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.SupplierCapabilities",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SupplierCapabilities.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.UnauthorizedResponse",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/UnauthorizedResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ValidationErrorDetail",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ValidationErrorDetail.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ValidationErrorItem",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ValidationErrorItem.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.declaration.ValidationErrorResponse",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ValidationErrorResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.detail-envelope",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/DetailEnvelope.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.health-response",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/HealthResponse.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.provider-status-response",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/ProviderStatusResponse.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.search-envelope",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SearchEnvelope.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.spn-batch-envelope",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnBatchEnvelope.json")
        ),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.spn-batch-request",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnBatchRequest.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.spn-envelope",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/SpnEnvelope.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.stream-done-event",
        include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/schema/StreamDoneEvent.json")),
    ),
    (
        "urn:supply-chain-monkey:schema:v1.stream-search-event",
        include_str!(
            concat!(env!("CARGO_MANIFEST_DIR"), "/schema/StreamSearchEvent.json")
        ),
    ),
];
