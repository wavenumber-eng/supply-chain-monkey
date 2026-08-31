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
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeMetadata`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
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
///      "type": "boolean"
///    },
///    "error": {
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
///      "type": "string"
///    },
///    "provider_capabilities": {
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
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "rate_limit": {
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
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    },
///    "status": {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_EnvelopeStatus"
///    },
///    "supplier": {
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeMetadata {
    pub cached: bool,
    pub error: ::std::option::Option<::std::string::String>,
    pub error_detail: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail,
    >,
    pub parameter_field_name: ::std::string::String,
    pub provider_capabilities: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    >,
    pub provider_latency_ms: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    pub rate_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot,
    >,
    pub service_timestamp: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    pub status: ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus,
    pub supplier: ::std::string::String,
}
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
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
///      "type": "string"
///    },
///    {
///      "type": "integer"
///    },
///    {
///      "type": "number"
///    },
///    {
///      "type": "boolean"
///    },
///    {
///      "type": "null"
///    },
///    {
///      "type": "array",
///      "items": {
///        "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonValue"
///      }
///    },
///    {
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
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationPart`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
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
///      "type": "string"
///    },
///    "description": {
///      "type": "string"
///    },
///    "extra_data": {
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
///      "type": "string"
///    },
///    "manufacturer": {
///      "type": "string"
///    },
///    "manufacturer_part_number": {
///      "type": "string"
///    },
///    "packaging": {
///      "type": "string"
///    },
///    "price_breaks": {
///      "type": "array",
///      "items": {
///        "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_PriceBreak"
///      }
///    },
///    "product_url": {
///      "type": "string"
///    },
///    "source_provider": {
///      "type": "string"
///    },
///    "stock_quantity": {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "stock_status": {
///      "type": "string"
///    },
///    "supplier": {
///      "type": "string"
///    },
///    "supplier_part_number": {
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationPart {
    pub datasheet_url: ::std::string::String,
    pub description: ::std::string::String,
    pub extra_data: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderRawData,
    >,
    pub lifecycle_status: ::std::string::String,
    pub manufacturer: ::std::string::String,
    pub manufacturer_part_number: ::std::string::String,
    pub packaging: ::std::string::String,
    pub price_breaks: ::std::vec::Vec<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationPriceBreak,
    >,
    pub product_url: ::std::string::String,
    pub source_provider: ::std::string::String,
    pub stock_quantity: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    pub stock_status: ::std::string::String,
    pub supplier: ::std::string::String,
    pub supplier_part_number: ::std::string::String,
}
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationPriceBreak`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "type": "object",
///  "required": [
///    "currency",
///    "qty",
///    "unit_price"
///  ],
///  "properties": {
///    "currency": {
///      "type": "string"
///    },
///    "qty": {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "unit_price": {
///      "type": "number"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationPriceBreak {
    pub currency: ::std::string::String,
    pub qty: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
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
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
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
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    },
///    "request_limit": {
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
    pub burst_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub burst_remaining: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub observed_at: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    pub request_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub requests_remaining: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub reset_seconds: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub reset_time: ::std::option::Option<::std::string::String>,
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
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "type": "object",
///  "required": [
///    "code",
///    "retryable",
///    "upstream_request_id",
///    "upstream_status_code"
///  ],
///  "properties": {
///    "code": {
///      "type": "string"
///    },
///    "retryable": {
///      "type": "boolean"
///    },
///    "upstream_request_id": {
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
    pub code: ::std::string::String,
    pub retryable: bool,
    pub upstream_request_id: ::std::option::Option<::std::string::String>,
    pub upstream_status_code: ::std::option::Option<i32>,
}
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
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
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///    },
///    "min_request_interval_seconds": {
///      "type": "number"
///    },
///    "notes": {
///      "type": "array",
///      "items": {
///        "type": "string"
///      }
///    },
///    "provider_kind": {
///      "type": "string"
///    },
///    "rate_limit_per_day": {
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
///      "type": "string"
///    },
///    "supports_keyword_search": {
///      "type": "boolean"
///    },
///    "supports_mpn_search": {
///      "type": "boolean"
///    },
///    "supports_native_spn_batch": {
///      "type": "boolean"
///    },
///    "supports_quota_headers": {
///      "type": "boolean"
///    },
///    "supports_spn_lookup": {
///      "type": "boolean"
///    },
///    "usage_unit": {
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities {
    pub max_spn_batch_size: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    pub min_request_interval_seconds: f64,
    pub notes: ::std::vec::Vec<::std::string::String>,
    pub provider_kind: ::std::string::String,
    pub rate_limit_per_day: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub rate_limit_per_minute: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    pub supplier: ::std::string::String,
    pub supports_keyword_search: bool,
    pub supports_mpn_search: bool,
    pub supports_native_spn_batch: bool,
    pub supports_quota_headers: bool,
    pub supports_spn_lookup: bool,
    pub usage_unit: ::std::string::String,
}
///`SearchEnvelope`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.search-envelope",
///  "title": "SearchEnvelope",
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
///      "anyOf": [
///        {
///          "type": "array",
///          "items": {
///            "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Part"
///          }
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
pub struct SearchEnvelope {
    pub cached: bool,
    pub data: ::std::option::Option<
        ::std::vec::Vec<ExternalUrnSupplyChainMonkeySchemaV1DeclarationPart>,
    >,
    pub error: ::std::option::Option<::std::string::String>,
    pub error_detail: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationServiceErrorDetail,
    >,
    pub parameter_field_name: ::std::string::String,
    pub provider_capabilities: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    >,
    pub provider_latency_ms: ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    pub rate_limit: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationRateLimitSnapshot,
    >,
    pub service_timestamp: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    pub status: ExternalUrnSupplyChainMonkeySchemaV1DeclarationEnvelopeStatus,
    pub supplier: ::std::string::String,
}
