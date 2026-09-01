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
///Request for multiple exact supplier-part-number lookups.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.spn-batch-request",
///  "title": "SpnBatchRequest",
///  "description": "Request for multiple exact supplier-part-number lookups.",
///  "type": "object",
///  "required": [
///    "spns",
///    "supplier"
///  ],
///  "properties": {
///    "include_raw": {
///      "description": "Include provider-owned raw data in returned parts.",
///      "default": false,
///      "type": "boolean"
///    },
///    "spns": {
///      "description": "Supplier part numbers to resolve; between one and 1,000 items.",
///      "type": "array",
///      "items": {
///        "type": "string"
///      },
///      "maxItems": 1000,
///      "minItems": 1
///    },
///    "supplier": {
///      "description": "Supplier whose part numbers should be resolved.",
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct SpnBatchRequest {
    ///Include provider-owned raw data in returned parts.
    #[serde(default)]
    pub include_raw: bool,
    ///Supplier part numbers to resolve; between one and 1,000 items.
    pub spns: ::std::vec::Vec<::std::string::String>,
    ///Supplier whose part numbers should be resolved.
    pub supplier: ::std::string::String,
}
