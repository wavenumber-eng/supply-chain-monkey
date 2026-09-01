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
///Configuration and capabilities reported for one provider.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Configuration and capabilities reported for one provider.",
///  "type": "object",
///  "required": [
///    "capabilities",
///    "configured"
///  ],
///  "properties": {
///    "backend": {
///      "description": "Selected backend implementation, when available.",
///      "type": "string"
///    },
///    "capabilities": {
///      "description": "Features and operational limits exposed by the provider.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_SupplierCapabilities"
///    },
///    "configured": {
///      "description": "Whether the provider is currently configured for use.",
///      "type": "boolean"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationProviderStatusEntry {
    ///Selected backend implementation, when available.
    #[serde(default, skip_serializing_if = "::std::option::Option::is_none")]
    pub backend: ::std::option::Option<::std::string::String>,
    ///Features and operational limits exposed by the provider.
    pub capabilities: ExternalUrnSupplyChainMonkeySchemaV1DeclarationSupplierCapabilities,
    ///Whether the provider is currently configured for use.
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
///Map of provider names to current configuration and capabilities.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.provider-status-response",
///  "title": "ProviderStatusResponse",
///  "description": "Map of provider names to current configuration and capabilities.",
///  "type": "object",
///  "required": [
///    "providers"
///  ],
///  "properties": {
///    "providers": {
///      "description": "Provider status keyed by canonical provider name.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_RecordProviderStatusEntry"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ProviderStatusResponse {
    ///Provider status keyed by canonical provider name.
    pub providers: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRecordProviderStatusEntry,
}
