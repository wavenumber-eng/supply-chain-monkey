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
///Account-data features currently exposed by SCM.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.account-capabilities-response",
///  "title": "AccountCapabilitiesResponse",
///  "description": "Account-data features currently exposed by SCM.",
///  "type": "object",
///  "required": [
///    "configured"
///  ],
///  "properties": {
///    "configured": {
///      "description": "Whether JLC private-library credentials are configured.",
///      "type": "boolean"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct AccountCapabilitiesResponse {
    ///Whether JLC private-library credentials are configured.
    pub configured: bool,
}
