#![allow(dead_code, reason = "generated roots contain projection helpers")]
/// Error types.
pub mod error {
    /// Error from a `TryFrom` or `FromStr` implementation.
    pub struct ConversionError(::std::borrow::Cow<'static, str>);
    impl ::std::error::Error for ConversionError {}
    impl ::std::fmt::Display for ConversionError {
        fn fmt(
            &self,
            f: &mut ::std::fmt::Formatter<'_>,
        ) -> Result<(), ::std::fmt::Error> {
            ::std::fmt::Display::fmt(&self.0, f)
        }
    }
    impl ::std::fmt::Debug for ConversionError {
        fn fmt(
            &self,
            f: &mut ::std::fmt::Formatter<'_>,
        ) -> Result<(), ::std::fmt::Error> {
            ::std::fmt::Debug::fmt(&self.0, f)
        }
    }
    impl From<&'static str> for ConversionError {
        fn from(value: &'static str) -> Self {
            Self(value.into())
        }
    }
    impl From<String> for ConversionError {
        fn from(value: String) -> Self {
            Self(value.into())
        }
    }
}
///Metadata shared by typed SCM operation envelopes.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Metadata shared by typed SCM operation envelopes.",
///  "type": "object",
///  "required": [
///    "cached",
///    "error",
///    "error_detail",
///    "parameter_field_name",
///    "provider_capabilities",
///    "provider_latency_ms",
///    "rate_limit",
///    "service_timestamp",
///    "status",
///    "supplier"
///  ],
///  "properties": {
///    "cached": {
///      "description": "Whether SCM returned a cached provider result.",
///      "type": "boolean"
///    },
///    "error": {
///      "description": "Sanitized human-readable error, or null for normal outcomes.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "error_detail": {
///      "description": "Sanitized structured error details, when available.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_ServiceErrorDetail"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "parameter_field_name": {
///      "description": "Query parameter name used to identify the requested part.",
///      "type": "string"
///    },
///    "provider_capabilities": {
///      "description": "Provider features known at request time.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_SupplierCapabilities"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "provider_latency_ms": {
///      "description": "Provider execution time measured by SCM in milliseconds.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "rate_limit": {
///      "description": "Provider rate-limit state observed for this request.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_RateLimitSnapshot"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "service_timestamp": {
///      "description": "Time at which SCM produced the response.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    },
///    "status": {
///      "description": "High-level provider outcome.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_EnvelopeStatus"
///    },
///    "supplier": {
///      "description": "Canonical or requested supplier name associated with the outcome.",
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeMetadata {
    ///Whether SCM returned a cached provider result.
    pub cached: bool,
    ///Sanitized human-readable error, or null for normal outcomes.
    pub error: ::std::option::Option<::std::string::String>,
    ///Sanitized structured error details, when available.
    pub error_detail: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail,
    >,
    ///Query parameter name used to identify the requested part.
    pub parameter_field_name: ::std::string::String,
    ///Provider features known at request time.
    pub provider_capabilities: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    >,
    ///Provider execution time measured by SCM in milliseconds.
    pub provider_latency_ms: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    ///Provider rate-limit state observed for this request.
    pub rate_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot,
    >,
    ///Time at which SCM produced the response.
    pub service_timestamp: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    ///High-level provider outcome.
    pub status: ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus,
    ///Canonical or requested supplier name associated with the outcome.
    pub supplier: ::std::string::String,
}
///High-level outcome reported by an SCM response envelope.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "High-level outcome reported by an SCM response envelope.",
///  "type": "string",
///  "enum": [
///    "ok",
///    "partial",
///    "not_found",
///    "provider_error"
///  ]
///}
/// ```
/// </details>
#[derive(
    ::serde::Deserialize,
    ::serde::Serialize,
    Clone,
    Copy,
    Debug,
    Eq,
    Hash,
    Ord,
    PartialEq,
    PartialOrd
)]
pub enum ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    #[serde(rename = "ok")]
    Ok,
    #[serde(rename = "partial")]
    Partial,
    #[serde(rename = "not_found")]
    NotFound,
    #[serde(rename = "provider_error")]
    ProviderError,
}
impl ::std::fmt::Display
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
        match *self {
            Self::Ok => f.write_str("ok"),
            Self::Partial => f.write_str("partial"),
            Self::NotFound => f.write_str("not_found"),
            Self::ProviderError => f.write_str("provider_error"),
        }
    }
}
impl ::std::str::FromStr
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    type Err = self::error::ConversionError;
    fn from_str(
        value: &str,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        match value {
            "ok" => Ok(Self::Ok),
            "partial" => Ok(Self::Partial),
            "not_found" => Ok(Self::NotFound),
            "provider_error" => Ok(Self::ProviderError),
            _ => Err("invalid value".into()),
        }
    }
}
impl ::std::convert::TryFrom<&str>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    type Error = self::error::ConversionError;
    fn try_from(
        value: &str,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
impl ::std::convert::TryFrom<&::std::string::String>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    type Error = self::error::ConversionError;
    fn try_from(
        value: &::std::string::String,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
impl ::std::convert::TryFrom<::std::string::String>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus {
    type Error = self::error::ConversionError;
    fn try_from(
        value: ::std::string::String,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
///I-JSON interoperable integer range used by SCM JSON payloads.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "I-JSON interoperable integer range used by SCM JSON payloads.",
///  "type": "integer",
///  "maximum": 9007199254740991.0,
///  "minimum": -9007199254740991.0
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(transparent)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger(pub i64);
impl ::std::ops::Deref for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    type Target = i64;
    fn deref(&self) -> &i64 {
        &self.0
    }
}
impl ::std::convert::From<ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger>
for i64 {
    fn from(value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger) -> Self {
        value.0
    }
}
impl ::std::convert::From<i64>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    fn from(value: i64) -> Self {
        Self(value)
    }
}
impl ::std::str::FromStr for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    type Err = <i64 as ::std::str::FromStr>::Err;
    fn from_str(value: &str) -> ::std::result::Result<Self, Self::Err> {
        Ok(Self(value.parse()?))
    }
}
impl ::std::convert::TryFrom<&str>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    type Error = <i64 as ::std::str::FromStr>::Err;
    fn try_from(value: &str) -> ::std::result::Result<Self, Self::Error> {
        value.parse()
    }
}
impl ::std::convert::TryFrom<String>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    type Error = <i64 as ::std::str::FromStr>::Err;
    fn try_from(value: String) -> ::std::result::Result<Self, Self::Error> {
        value.parse()
    }
}
impl ::std::fmt::Display for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger {
    fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
        self.0.fmt(f)
    }
}
///JSON-compatible scalar, array, or object value.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "JSON-compatible scalar, array, or object value.",
///  "anyOf": [
///    {
///      "description": "JSON string value.",
///      "type": "string"
///    },
///    {
///      "type": "integer"
///    },
///    {
///      "description": "JSON number value.",
///      "type": "number"
///    },
///    {
///      "description": "JSON boolean value.",
///      "type": "boolean"
///    },
///    {
///      "description": "JSON null value.",
///      "type": "null"
///    },
///    {
///      "description": "JSON array containing recursively compatible values.",
///      "type": "array",
///      "items": {
///        "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonValue"
///      }
///    },
///    {
///      "description": "JSON object containing recursively compatible values.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_RecordJsonValue"
///    }
///  ]
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(untagged)]
pub enum ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    String(::std::string::String),
    Integer(i64),
    Number(f64),
    Boolean(bool),
    Null,
    Array(::std::vec::Vec<ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue>),
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue(
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue,
    ),
}
impl ::std::convert::From<i64>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    fn from(value: i64) -> Self {
        Self::Integer(value)
    }
}
impl ::std::convert::From<f64>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    fn from(value: f64) -> Self {
        Self::Number(value)
    }
}
impl ::std::convert::From<bool>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    fn from(value: bool) -> Self {
        Self::Boolean(value)
    }
}
impl ::std::convert::From<
    ::std::vec::Vec<ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue>,
> for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    fn from(
        value: ::std::vec::Vec<ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue>,
    ) -> Self {
        Self::Array(value)
    }
}
impl ::std::convert::From<ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue {
    fn from(
        value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue,
    ) -> Self {
        Self::ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue(value)
    }
}
///Normalized electronic-component result returned by supplier operations.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Normalized electronic-component result returned by supplier operations.",
///  "type": "object",
///  "required": [
///    "datasheet_url",
///    "description",
///    "extra_data",
///    "lifecycle_status",
///    "manufacturer",
///    "manufacturer_part_number",
///    "packaging",
///    "price_breaks",
///    "product_url",
///    "source_provider",
///    "stock_quantity",
///    "stock_status",
///    "supplier",
///    "supplier_part_number"
///  ],
///  "properties": {
///    "datasheet_url": {
///      "description": "Datasheet URL, or an empty string when unavailable.",
///      "type": "string"
///    },
///    "description": {
///      "description": "Human-readable supplier description.",
///      "type": "string"
///    },
///    "extra_data": {
///      "description": "Provider-owned data, present only when explicitly requested.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_ProviderRawData"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "lifecycle_status": {
///      "description": "Supplier-reported lifecycle state.",
///      "type": "string"
///    },
///    "manufacturer": {
///      "description": "Component manufacturer name.",
///      "type": "string"
///    },
///    "manufacturer_part_number": {
///      "description": "Manufacturer-owned part number.",
///      "type": "string"
///    },
///    "packaging": {
///      "description": "Supplier-reported packaging description.",
///      "type": "string"
///    },
///    "price_breaks": {
///      "description": "Quantity-based prices in provider order.",
///      "type": "array",
///      "items": {
///        "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_PriceBreak"
///      }
///    },
///    "product_url": {
///      "description": "Supplier product-page URL, or an empty string when unavailable.",
///      "type": "string"
///    },
///    "source_provider": {
///      "description": "Backend that produced the normalized result.",
///      "type": "string"
///    },
///    "stock_quantity": {
///      "description": "Supplier-reported available stock quantity.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "stock_status": {
///      "description": "Human-readable supplier stock status.",
///      "type": "string"
///    },
///    "supplier": {
///      "description": "Canonical supplier associated with this result.",
///      "type": "string"
///    },
///    "supplier_part_number": {
///      "description": "Supplier-owned ordering or catalog number.",
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationPart {
    ///Datasheet URL, or an empty string when unavailable.
    pub datasheet_url: ::std::string::String,
    ///Human-readable supplier description.
    pub description: ::std::string::String,
    ///Provider-owned data, present only when explicitly requested.
    pub extra_data: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData,
    >,
    ///Supplier-reported lifecycle state.
    pub lifecycle_status: ::std::string::String,
    ///Component manufacturer name.
    pub manufacturer: ::std::string::String,
    ///Manufacturer-owned part number.
    pub manufacturer_part_number: ::std::string::String,
    ///Supplier-reported packaging description.
    pub packaging: ::std::string::String,
    ///Quantity-based prices in provider order.
    pub price_breaks: ::std::vec::Vec<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationPriceBreak,
    >,
    ///Supplier product-page URL, or an empty string when unavailable.
    pub product_url: ::std::string::String,
    ///Backend that produced the normalized result.
    pub source_provider: ::std::string::String,
    ///Supplier-reported available stock quantity.
    pub stock_quantity: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    ///Human-readable supplier stock status.
    pub stock_status: ::std::string::String,
    ///Canonical supplier associated with this result.
    pub supplier: ::std::string::String,
    ///Supplier-owned ordering or catalog number.
    pub supplier_part_number: ::std::string::String,
}
///One quantity-based unit-price offer normalized from a supplier.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "One quantity-based unit-price offer normalized from a supplier.",
///  "type": "object",
///  "required": [
///    "currency",
///    "qty",
///    "unit_price"
///  ],
///  "properties": {
///    "currency": {
///      "description": "Supplier-reported ISO-style currency code.",
///      "type": "string"
///    },
///    "qty": {
///      "description": "Minimum order quantity for this unit price.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "unit_price": {
///      "description": "Price per component at the associated quantity.",
///      "type": "number"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationPriceBreak {
    ///Supplier-reported ISO-style currency code.
    pub currency: ::std::string::String,
    ///Minimum order quantity for this unit price.
    pub qty: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    ///Price per component at the associated quantity.
    pub unit_price: f64,
}
///The one reviewed provider-owned flexible JSON object.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "The one reviewed provider-owned flexible JSON object.",
///  "type": "object",
///  "additionalProperties": {
///    "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonValue"
///  },
///  "x-wn-flexible": true,
///  "x-wn-flexible-reason": "Raw provider data is returned only when include_raw is explicitly requested."
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(transparent)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData(
    pub ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >,
);
impl ::std::ops::Deref
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData {
    type Target = ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >;
    fn deref(
        &self,
    ) -> &::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    > {
        &self.0
    }
}
impl ::std::convert::From<ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData>
for ::std::collections::HashMap<
    ::std::string::String,
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
> {
    fn from(
        value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData,
    ) -> Self {
        value.0
    }
}
impl ::std::convert::From<
    ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >,
> for ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData {
    fn from(
        value: ::std::collections::HashMap<
            ::std::string::String,
            ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
        >,
    ) -> Self {
        Self(value)
    }
}
///Rate-limit information observed on the provider response.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Rate-limit information observed on the provider response.",
///  "type": "object",
///  "required": [
///    "burst_limit",
///    "burst_remaining",
///    "observed_at",
///    "request_limit",
///    "requests_remaining",
///    "reset_seconds",
///    "reset_time",
///    "retry_after_seconds"
///  ],
///  "properties": {
///    "burst_limit": {
///      "description": "Burst quota, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "burst_remaining": {
///      "description": "Burst requests remaining, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "observed_at": {
///      "description": "Time at which SCM observed this rate-limit state.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    },
///    "request_limit": {
///      "description": "Total request quota, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "requests_remaining": {
///      "description": "Requests remaining in the current quota window, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "reset_seconds": {
///      "description": "Seconds until the quota resets, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "reset_time": {
///      "description": "Provider-formatted quota reset time, when reported.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "retry_after_seconds": {
///      "description": "Provider-requested retry delay in seconds, when reported.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot {
    ///Burst quota, when reported.
    pub burst_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Burst requests remaining, when reported.
    pub burst_remaining: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Time at which SCM observed this rate-limit state.
    pub observed_at: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    ///Total request quota, when reported.
    pub request_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Requests remaining in the current quota window, when reported.
    pub requests_remaining: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Seconds until the quota resets, when reported.
    pub reset_seconds: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Provider-formatted quota reset time, when reported.
    pub reset_time: ::std::option::Option<::std::string::String>,
    ///Provider-requested retry delay in seconds, when reported.
    pub retry_after_seconds: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
}
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "type": "object",
///  "additionalProperties": {
///    "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonValue"
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(transparent)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue(
    pub ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >,
);
impl ::std::ops::Deref
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue {
    type Target = ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >;
    fn deref(
        &self,
    ) -> &::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    > {
        &self.0
    }
}
impl ::std::convert::From<ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue>
for ::std::collections::HashMap<
    ::std::string::String,
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
> {
    fn from(
        value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue,
    ) -> Self {
        value.0
    }
}
impl ::std::convert::From<
    ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
    >,
> for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordJsonValue {
    fn from(
        value: ::std::collections::HashMap<
            ::std::string::String,
            ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonValue,
        >,
    ) -> Self {
        Self(value)
    }
}
///RFC 3339 timestamp retained as the deployed Python string representation.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "RFC 3339 timestamp retained as the deployed Python string representation.",
///  "type": "string",
///  "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$"
///}
/// ```
/// </details>
#[derive(::serde::Serialize, Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
#[serde(transparent)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp(
    ::std::string::String,
);
impl ::std::ops::Deref
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    type Target = ::std::string::String;
    fn deref(&self) -> &::std::string::String {
        &self.0
    }
}
impl ::std::convert::From<
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
> for ::std::string::String {
    fn from(
        value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    ) -> Self {
        value.0
    }
}
impl ::std::str::FromStr
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    type Err = self::error::ConversionError;
    fn from_str(
        value: &str,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        static PATTERN: ::std::sync::LazyLock<::regress::Regex> = ::std::sync::LazyLock::new(||
        {
            ::regress::Regex::new(
                    "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$",
                )
                .unwrap()
        });
        if PATTERN.find(value).is_none() {
            return Err(
                "doesn't match pattern \"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$\""
                    .into(),
            );
        }
        Ok(Self(value.to_string()))
    }
}
impl ::std::convert::TryFrom<&str>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    type Error = self::error::ConversionError;
    fn try_from(
        value: &str,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
impl ::std::convert::TryFrom<&::std::string::String>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    type Error = self::error::ConversionError;
    fn try_from(
        value: &::std::string::String,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
impl ::std::convert::TryFrom<::std::string::String>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    type Error = self::error::ConversionError;
    fn try_from(
        value: ::std::string::String,
    ) -> ::std::result::Result<Self, self::error::ConversionError> {
        value.parse()
    }
}
impl<'de> ::serde::Deserialize<'de>
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp {
    fn deserialize<D>(deserializer: D) -> ::std::result::Result<Self, D::Error>
    where
        D: ::serde::Deserializer<'de>,
    {
        ::std::string::String::deserialize(deserializer)?
            .parse()
            .map_err(|e: self::error::ConversionError| {
                <D::Error as ::serde::de::Error>::custom(e.to_string())
            })
    }
}
///Sanitized machine-readable context for a provider failure.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Sanitized machine-readable context for a provider failure.",
///  "type": "object",
///  "required": [
///    "code",
///    "retryable",
///    "upstream_request_id",
///    "upstream_status_code"
///  ],
///  "properties": {
///    "code": {
///      "description": "Stable SCM error category.",
///      "type": "string"
///    },
///    "retryable": {
///      "description": "Whether retrying later may succeed.",
///      "type": "boolean"
///    },
///    "upstream_request_id": {
///      "description": "Sanitized upstream request identifier, when available.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "upstream_status_code": {
///      "description": "Sanitized upstream HTTP status, when available.",
///      "anyOf": [
///        {
///          "type": "integer",
///          "maximum": 2147483647.0,
///          "minimum": -2147483648.0
///        },
///        {
///          "type": "null"
///        }
///      ]
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail {
    ///Stable SCM error category.
    pub code: ::std::string::String,
    ///Whether retrying later may succeed.
    pub retryable: bool,
    ///Sanitized upstream request identifier, when available.
    pub upstream_request_id: ::std::option::Option<::std::string::String>,
    ///Sanitized upstream HTTP status, when available.
    pub upstream_status_code: ::std::option::Option<i32>,
}
///Search and lookup features exposed by one configured provider backend.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Search and lookup features exposed by one configured provider backend.",
///  "type": "object",
///  "required": [
///    "max_spn_batch_size",
///    "min_request_interval_seconds",
///    "notes",
///    "provider_kind",
///    "rate_limit_per_day",
///    "rate_limit_per_minute",
///    "supplier",
///    "supports_keyword_search",
///    "supports_mpn_search",
///    "supports_native_spn_batch",
///    "supports_quota_headers",
///    "supports_spn_lookup",
///    "usage_unit"
///  ],
///  "properties": {
///    "max_spn_batch_size": {
///      "description": "Maximum batch size accepted by SCM for this provider.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "min_request_interval_seconds": {
///      "description": "Minimum delay SCM applies between provider requests.",
///      "type": "number"
///    },
///    "notes": {
///      "description": "Human-readable capability and operational notes.",
///      "type": "array",
///      "items": {
///        "type": "string"
///      }
///    },
///    "provider_kind": {
///      "description": "Implementation category used for provider diagnostics.",
///      "type": "string"
///    },
///    "rate_limit_per_day": {
///      "description": "Provider request quota per day, when known.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "rate_limit_per_minute": {
///      "description": "Provider request quota per minute, when known.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "supplier": {
///      "description": "Canonical supplier represented by the backend.",
///      "type": "string"
///    },
///    "supports_keyword_search": {
///      "description": "Whether general keyword search is supported.",
///      "type": "boolean"
///    },
///    "supports_mpn_search": {
///      "description": "Whether manufacturer-part-number search is supported.",
///      "type": "boolean"
///    },
///    "supports_native_spn_batch": {
///      "description": "Whether the upstream provider has a native batch lookup.",
///      "type": "boolean"
///    },
///    "supports_quota_headers": {
///      "description": "Whether upstream quota headers are exposed in envelope metadata.",
///      "type": "boolean"
///    },
///    "supports_spn_lookup": {
///      "description": "Whether exact supplier-part-number lookup is supported.",
///      "type": "boolean"
///    },
///    "usage_unit": {
///      "description": "Unit consumed by one reported quota usage event.",
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities {
    ///Maximum batch size accepted by SCM for this provider.
    pub max_spn_batch_size: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    ///Minimum delay SCM applies between provider requests.
    pub min_request_interval_seconds: f64,
    ///Human-readable capability and operational notes.
    pub notes: ::std::vec::Vec<::std::string::String>,
    ///Implementation category used for provider diagnostics.
    pub provider_kind: ::std::string::String,
    ///Provider request quota per day, when known.
    pub rate_limit_per_day: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Provider request quota per minute, when known.
    pub rate_limit_per_minute: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///Canonical supplier represented by the backend.
    pub supplier: ::std::string::String,
    ///Whether general keyword search is supported.
    pub supports_keyword_search: bool,
    ///Whether manufacturer-part-number search is supported.
    pub supports_mpn_search: bool,
    ///Whether the upstream provider has a native batch lookup.
    pub supports_native_spn_batch: bool,
    ///Whether upstream quota headers are exposed in envelope metadata.
    pub supports_quota_headers: bool,
    ///Whether exact supplier-part-number lookup is supported.
    pub supports_spn_lookup: bool,
    ///Unit consumed by one reported quota usage event.
    pub usage_unit: ::std::string::String,
}
///Result envelope for exact supplier-part-number lookup.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.spn-envelope",
///  "title": "SpnEnvelope",
///  "description": "Result envelope for exact supplier-part-number lookup.",
///  "type": "object",
///  "allOf": [
///    {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_EnvelopeMetadata"
///    }
///  ],
///  "required": [
///    "data"
///  ],
///  "properties": {
///    "data": {
///      "description": "Resolved normalized part, or null when unavailable.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Part"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct SpnEnvelope {
    ///Whether SCM returned a cached provider result.
    pub cached: bool,
    ///Resolved normalized part, or null when unavailable.
    pub data: ::std::option::Option<ExternalUrnSupplyChainMonkeySchemaV1DeclarationPart>,
    ///Sanitized human-readable error, or null for normal outcomes.
    pub error: ::std::option::Option<::std::string::String>,
    ///Sanitized structured error details, when available.
    pub error_detail: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail,
    >,
    ///Query parameter name used to identify the requested part.
    pub parameter_field_name: ::std::string::String,
    ///Provider features known at request time.
    pub provider_capabilities: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    >,
    ///Provider execution time measured by SCM in milliseconds.
    pub provider_latency_ms: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    ///Provider rate-limit state observed for this request.
    pub rate_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot,
    >,
    ///Time at which SCM produced the response.
    pub service_timestamp: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    ///High-level provider outcome.
    pub status: ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus,
    ///Canonical or requested supplier name associated with the outcome.
    pub supplier: ::std::string::String,
}
