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
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "type": "object",
///  "required": [
///    "capabilities",
///    "configured"
///  ],
///  "properties": {
///    "backend": {
///      "type": "string"
///    },
///    "capabilities": {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_SupplierCapabilities"
///    },
///    "configured": {
///      "type": "boolean"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry {
    #[serde(default, skip_serializing_if = "::std::option::Option::is_none")]
    pub backend: ::std::option::Option<::std::string::String>,
    pub capabilities: ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    pub configured: bool,
}
///`ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "type": "object",
///  "additionalProperties": {
///    "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_ProviderStatusEntry"
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(transparent)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry(
    pub ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
    >,
);
impl ::std::ops::Deref
for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry {
    type Target = ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
    >;
    fn deref(
        &self,
    ) -> &::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
    > {
        &self.0
    }
}
impl ::std::convert::From<
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry,
>
for ::std::collections::HashMap<
    ::std::string::String,
    ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
> {
    fn from(
        value: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry,
    ) -> Self {
        value.0
    }
}
impl ::std::convert::From<
    ::std::collections::HashMap<
        ::std::string::String,
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
    >,
> for ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry {
    fn from(
        value: ::std::collections::HashMap<
            ::std::string::String,
            ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry,
        >,
    ) -> Self {
        Self(value)
    }
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
///`ProviderStatusResponse`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.provider-status-response",
///  "title": "ProviderStatusResponse",
///  "type": "object",
///  "required": [
///    "providers"
///  ],
///  "properties": {
///    "providers": {
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_RecordProviderStatusEntry"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ProviderStatusResponse {
    pub providers: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry,
}
