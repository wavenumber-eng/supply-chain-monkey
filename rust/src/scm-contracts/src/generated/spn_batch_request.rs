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
///`SpnBatchRequest`
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.spn-batch-request",
///  "title": "SpnBatchRequest",
///  "type": "object",
///  "required": [
///    "spns",
///    "supplier"
///  ],
///  "properties": {
///    "include_raw": {
///      "type": "boolean"
///    },
///    "spns": {
///      "type": "array",
///      "items": {
///        "type": "string"
///      },
///      "maxItems": 1000,
///      "minItems": 1
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
pub struct SpnBatchRequest {
    #[serde(default, skip_serializing_if = "::std::option::Option::is_none")]
    pub include_raw: ::std::option::Option<bool>,
    pub spns: ::std::vec::Vec<::std::string::String>,
    pub supplier: ::std::string::String,
}
