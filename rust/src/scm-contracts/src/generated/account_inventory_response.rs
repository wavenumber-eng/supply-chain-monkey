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
///One bounded live scan of the JLC account library.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "$id": "urn:supply-chain-monkey:schema:v1.account-inventory-response",
///  "title": "AccountInventoryResponse",
///  "description": "One bounded live scan of the JLC account library.",
///  "type": "object",
///  "required": [
///    "items",
///    "observed_at"
///  ],
///  "properties": {
///    "items": {
///      "description": "Account-library records observed in the complete bounded scan.",
///      "type": "array",
///      "items": {
///        "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_AccountInventoryRecord"
///      }
///    },
///    "observed_at": {
///      "description": "Time SCM completed the scan.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct AccountInventoryResponse {
    ///Account-library records observed in the complete bounded scan.
    pub items: ::std::vec::Vec<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationAccountInventoryRecord,
    >,
    ///Time SCM completed the scan.
    pub observed_at: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
}
///One component in the customer's JLC My Parts Lib.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "One component in the customer's JLC My Parts Lib.",
///  "type": "object",
///  "required": [
///    "balances",
///    "description",
///    "manufacturer",
///    "manufacturer_part_number",
///    "observed_at",
///    "supplier_part_number"
///  ],
///  "properties": {
///    "balances": {
///      "description": "Four separate JLC source counts; never a combined build quantity.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_AccountStockBalances"
///    },
///    "description": {
///      "description": "JLC component specification, when supplied.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "manufacturer": {
///      "description": "Brand reported for this JLC component, when supplied.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "manufacturer_part_number": {
///      "description": "JLC component model, when supplied; it may be shared by multiple C-codes.",
///      "anyOf": [
///        {
///          "type": "string"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "observed_at": {
///      "description": "Time SCM fetched this page, not a supplier snapshot time.",
///      "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_Rfc3339Timestamp"
///    },
///    "supplier_part_number": {
///      "description": "JLC C-code used to identify the component.",
///      "type": "string"
///    }
///  }
///}
/// ```
/// </details>
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug)]
#[serde(deny_unknown_fields)]
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationAccountInventoryRecord {
    ///Four separate JLC source counts; never a combined build quantity.
    pub balances: ExternalUrnSupplyChainMonkeySchemaV1DeclarationAccountStockBalances,
    ///JLC component specification, when supplied.
    pub description: ::std::option::Option<::std::string::String>,
    ///Brand reported for this JLC component, when supplied.
    pub manufacturer: ::std::option::Option<::std::string::String>,
    ///JLC component model, when supplied; it may be shared by multiple C-codes.
    pub manufacturer_part_number: ::std::option::Option<::std::string::String>,
    ///Time SCM fetched this page, not a supplier snapshot time.
    pub observed_at: ExternalUrnSupplyChainMonkeySchemaV1DeclarationRfc3339Timestamp,
    ///JLC C-code used to identify the component.
    pub supplier_part_number: ::std::string::String,
}
///Four separate JLC source counts, with null distinct from zero.
///
/// <details><summary>JSON schema</summary>
///
/// ```json
///{
///  "description": "Four separate JLC source counts, with null distinct from zero.",
///  "type": "object",
///  "required": [
///    "consigned_parts",
///    "global_sourcing_parts",
///    "idle_stock",
///    "jlcpcb_parts"
///  ],
///  "properties": {
///    "consigned_parts": {
///      "description": "JLC `consignedParts` count.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "global_sourcing_parts": {
///      "description": "JLC `globalSourcingParts` count.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "idle_stock": {
///      "description": "JLC `idleStock` count.",
///      "anyOf": [
///        {
///          "$ref": "#/$defs/External_urn_supply_chain_monkey_schema_v1_declaration_JsonInteger"
///        },
///        {
///          "type": "null"
///        }
///      ]
///    },
///    "jlcpcb_parts": {
///      "description": "JLC `jlcpcbParts` count.",
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
pub struct ExternalUrnSupplyChainMonkeySchemaV1DeclarationAccountStockBalances {
    ///JLC `consignedParts` count.
    pub consigned_parts: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///JLC `globalSourcingParts` count.
    pub global_sourcing_parts: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///JLC `idleStock` count.
    pub idle_stock: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
    ///JLC `jlcpcbParts` count.
    pub jlcpcb_parts: ::std::option::Option<
        ExternalUrnSupplyChainMonkeySchemaV1DeclarationJsonInteger,
    >,
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
