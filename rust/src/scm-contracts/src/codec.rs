//! Strict bounded I-JSON and schema codec.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::sync::OnceLock;

use jsonschema::{Retrieve, Uri, Validator};
use serde::Serialize;
use serde::de::{DeserializeOwned, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Value};
use thiserror::Error;

use crate::{ContractRoot, GENERATED_SCHEMAS};

/// Default maximum encoded payload size accepted by the contract codec.
pub const DEFAULT_MAX_BYTES: usize = 8 * 1024 * 1024;
const MIN_IJSON_INTEGER: i64 = -9_007_199_254_740_991;
const MAX_IJSON_INTEGER: u64 = 9_007_199_254_740_991;

/// Failure while preflighting, validating, or decoding an SCM contract.
#[derive(Debug, Error)]
pub enum CodecError {
    /// Payload exceeded its configured byte limit.
    #[error("payload is {actual} bytes; limit is {limit}")]
    PayloadTooLarge {
        /// Number of bytes presented to the codec.
        actual: usize,
        /// Maximum number of bytes accepted by the caller.
        limit: usize,
    },
    /// Payload was not strict I-JSON.
    #[error("invalid strict JSON: {0}")]
    Json(String),
    /// Payload did not satisfy the selected unmodified generated schema.
    #[error("schema validation failed: {0}")]
    Schema(String),
    /// Payload could not be represented by the generated native model.
    #[error("generated model conversion failed: {0}")]
    Model(String),
}

/// Decode bounded strict JSON through schema validation into a generated type.
pub fn decode<T: DeserializeOwned>(
    root: ContractRoot,
    payload: &[u8],
    max_bytes: usize,
) -> Result<T, CodecError> {
    check_size(payload.len(), max_bytes)?;
    let value = strict_value(payload)?;
    validate(root, &value)?;
    serde_json::from_value(value).map_err(|error| CodecError::Model(error.to_string()))
}

/// Encode a generated type only after validation against its root schema.
pub fn encode<T: Serialize>(
    root: ContractRoot,
    model: &T,
    max_bytes: usize,
) -> Result<Vec<u8>, CodecError> {
    let value =
        serde_json::to_value(model).map_err(|error| CodecError::Model(error.to_string()))?;
    check_ijson(&value, "$")?;
    validate(root, &value)?;
    let payload =
        serde_json::to_vec(&value).map_err(|error| CodecError::Json(error.to_string()))?;
    check_size(payload.len(), max_bytes)?;
    Ok(payload)
}

fn check_size(actual: usize, limit: usize) -> Result<(), CodecError> {
    if actual > limit {
        return Err(CodecError::PayloadTooLarge { actual, limit });
    }
    Ok(())
}

fn strict_value(payload: &[u8]) -> Result<Value, CodecError> {
    let mut deserializer = serde_json::Deserializer::from_slice(payload);
    let value = deserializer
        .deserialize_any(StrictValueVisitor)
        .map_err(|error| CodecError::Json(error.to_string()))?;
    deserializer
        .end()
        .map_err(|error| CodecError::Json(error.to_string()))?;
    check_ijson(&value, "$")?;
    Ok(value)
}

fn check_ijson(value: &Value, path: &str) -> Result<(), CodecError> {
    match value {
        Value::Number(number) => {
            let valid = if let Some(value) = number.as_i64() {
                (MIN_IJSON_INTEGER..=MAX_IJSON_INTEGER as i64).contains(&value)
            } else if let Some(value) = number.as_u64() {
                value <= MAX_IJSON_INTEGER
            } else {
                number.as_f64().is_some_and(f64::is_finite)
            };
            if !valid {
                return Err(CodecError::Json(format!("non-I-JSON number at {path}")));
            }
        }
        Value::Array(items) => {
            for (index, item) in items.iter().enumerate() {
                check_ijson(item, &format!("{path}[{index}]"))?;
            }
        }
        Value::Object(object) => {
            for (key, item) in object {
                check_ijson(item, &format!("{path}.{key}"))?;
            }
        }
        _ => {}
    }
    Ok(())
}

fn validate(root: ContractRoot, instance: &Value) -> Result<(), CodecError> {
    let validator = validators()?
        .get(root.schema_id())
        .ok_or_else(|| CodecError::Schema(format!("missing root schema: {}", root.schema_id())))?;
    validator
        .validate(instance)
        .map_err(|error| CodecError::Schema(error.to_string()))
}

static VALIDATORS: OnceLock<Result<HashMap<&'static str, Validator>, String>> = OnceLock::new();

fn validators() -> Result<&'static HashMap<&'static str, Validator>, CodecError> {
    VALIDATORS
        .get_or_init(build_validators)
        .as_ref()
        .map_err(|error| CodecError::Schema(error.clone()))
}

fn build_validators() -> Result<HashMap<&'static str, Validator>, String> {
    let retriever = SchemaRetriever::new().map_err(|error| error.to_string())?;
    let mut validators = HashMap::new();
    for root in ContractRoot::ALL {
        let schema = retriever
            .schemas
            .get(root.schema_id())
            .ok_or_else(|| format!("missing root schema: {}", root.schema_id()))?;
        let validator = jsonschema::options()
            .with_retriever(retriever.clone())
            .build(schema)
            .map_err(|error| error.to_string())?;
        validators.insert(root.schema_id(), validator);
    }
    Ok(validators)
}

#[derive(Clone, Debug)]
struct SchemaRetriever {
    schemas: HashMap<String, Value>,
}

impl SchemaRetriever {
    fn new() -> Result<Self, CodecError> {
        let mut schemas = HashMap::new();
        for (schema_id, source) in GENERATED_SCHEMAS {
            let value: Value = serde_json::from_str(source)
                .map_err(|error| CodecError::Schema(error.to_string()))?;
            schemas.insert((*schema_id).to_owned(), value.clone());
            if schema_id.ends_with(".json") {
                schemas.insert(format!("urn:{schema_id}"), value);
            }
        }
        Ok(Self { schemas })
    }
}

impl Retrieve for SchemaRetriever {
    fn retrieve(
        &self,
        uri: &Uri<String>,
    ) -> Result<Value, Box<dyn std::error::Error + Send + Sync>> {
        self.schemas
            .get(uri.as_str())
            .cloned()
            .ok_or_else(|| format!("SCM schema not found: {uri}").into())
    }
}

struct StrictValueVisitor;

impl<'de> Visitor<'de> for StrictValueVisitor {
    type Value = Value;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a strict JSON value")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Value, E> {
        Ok(Value::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Value, E> {
        Ok(Value::Number(value.into()))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Value, E> {
        Ok(Value::Number(value.into()))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Value, E>
    where
        E: serde::de::Error,
    {
        serde_json::Number::from_f64(value)
            .map(Value::Number)
            .ok_or_else(|| E::custom("non-finite number"))
    }

    fn visit_str<E>(self, value: &str) -> Result<Value, E> {
        Ok(Value::String(value.to_owned()))
    }

    fn visit_string<E>(self, value: String) -> Result<Value, E> {
        Ok(Value::String(value))
    }

    fn visit_none<E>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }

    fn visit_unit<E>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(Self)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element_seed(StrictValueSeed)? {
            values.push(value);
        }
        Ok(Value::Array(values))
    }

    fn visit_map<A>(self, mut map: A) -> Result<Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut keys = HashSet::new();
        let mut values = Map::new();
        while let Some(key) = map.next_key::<String>()? {
            if !keys.insert(key.clone()) {
                return Err(serde::de::Error::custom(format!(
                    "duplicate object member: {key}"
                )));
            }
            values.insert(key, map.next_value_seed(StrictValueSeed)?);
        }
        Ok(Value::Object(values))
    }
}

struct StrictValueSeed;

impl<'de> serde::de::DeserializeSeed<'de> for StrictValueSeed {
    type Value = Value;

    fn deserialize<D>(self, deserializer: D) -> Result<Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictValueVisitor)
    }
}
