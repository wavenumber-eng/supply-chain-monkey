//! Explicit compatibility with serde_json's opt-in number representation.

use serde::de::{DeserializeSeed, Deserializer, MapAccess, Visitor};
use serde_json::{Number, Value};

use super::{CodecError, MAX_IJSON_INTEGER, MIN_IJSON_INTEGER};

const NUMBER_KEY: &str = "$serde_json::private::Number";

pub(super) enum MapKey {
    Object(String),
    Number,
}

pub(super) struct MapKeySeed;

impl<'de> DeserializeSeed<'de> for MapKeySeed {
    type Value = MapKey;

    fn deserialize<D>(self, deserializer: D) -> Result<MapKey, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_str(self)
    }
}

impl Visitor<'_> for MapKeySeed {
    type Value = MapKey;

    fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("a JSON object key")
    }

    fn visit_str<E>(self, value: &str) -> Result<MapKey, E> {
        Ok(if value == NUMBER_KEY {
            MapKey::Number
        } else {
            MapKey::Object(value.into())
        })
    }

    fn visit_string<E>(self, value: String) -> Result<MapKey, E> {
        Ok(if value == NUMBER_KEY {
            MapKey::Number
        } else {
            MapKey::Object(value)
        })
    }
}

pub(super) fn read_number<'de, A>(map: &mut A) -> Result<Value, A::Error>
where
    A: MapAccess<'de>,
{
    let raw: String = map.next_value()?;
    if map.next_key::<String>()?.is_some() {
        return Err(serde::de::Error::custom("number contains trailing fields"));
    }
    let number = raw.parse::<Number>().map_err(serde::de::Error::custom)?;
    if !valid_number(&number) {
        return Err(serde::de::Error::custom("non-I-JSON number"));
    }
    // Preserve the default codec's finite binary64 semantics. A noncanonical
    // exponent lexeme can otherwise re-enter serde as a map during from_value,
    // changing generated untagged JsonValue numbers into ordinary objects.
    if number.as_str().contains(['.', 'e', 'E']) {
        return number
            .as_f64()
            .and_then(Number::from_f64)
            .map(Value::Number)
            .ok_or_else(|| serde::de::Error::custom("non-finite number"));
    }
    Ok(Value::Number(number))
}

pub(super) fn valid_number(number: &Number) -> bool {
    if number.as_str().contains(['.', 'e', 'E']) {
        return number.as_f64().is_some_and(f64::is_finite);
    }
    if let Some(value) = number.as_i64() {
        return (MIN_IJSON_INTEGER..=MAX_IJSON_INTEGER as i64).contains(&value);
    }
    number
        .as_u64()
        .is_some_and(|value| value <= MAX_IJSON_INTEGER)
}

pub(super) fn check_key(key: &str) -> Result<(), CodecError> {
    if key == NUMBER_KEY {
        return Err(CodecError::Json(
            "object contains a reserved decoder key".into(),
        ));
    }
    Ok(())
}

// The synthetic singleton map must not be forgeable by an authored JSON object.
// Inspect original key strings before serde exposes numbers through MapAccess.
pub(super) fn reject_reserved_keys(raw: &[u8]) -> Result<(), CodecError> {
    let mut index = 0;
    while let Some(byte) = raw.get(index) {
        if *byte != b'"' {
            index += 1;
            continue;
        }
        let start = index;
        let Some((end, candidate)) = string_end(raw, index + 1) else {
            break;
        };
        index = end;
        if !candidate {
            continue;
        }
        let mut delimiter = end;
        while matches!(raw.get(delimiter), Some(b' ' | b'\t' | b'\r' | b'\n')) {
            delimiter += 1;
        }
        if raw.get(delimiter) == Some(&b':')
            && let Ok(key) = serde_json::from_slice::<String>(&raw[start..end])
        {
            check_key(&key)?;
        }
    }
    Ok(())
}

fn string_end(raw: &[u8], mut index: usize) -> Option<(usize, bool)> {
    let mut candidate = false;
    while let Some(byte) = raw.get(index) {
        match byte {
            b'\\' => {
                candidate = true;
                index += 2;
            }
            b'$' => {
                candidate = true;
                index += 1;
            }
            b'"' => return Some((index + 1, candidate)),
            _ => index += 1,
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::de::value::{Error, MapDeserializer};

    #[test]
    fn synthetic_number_map_requires_exactly_one_valid_numeric_string() {
        for entries in [
            vec![(NUMBER_KEY, "0.25"), ("tail", "extra")],
            vec![(NUMBER_KEY, "NaN")],
        ] {
            let mut map = MapDeserializer::<_, Error>::new(entries.into_iter());
            assert_eq!(
                map.next_key::<String>().unwrap().as_deref(),
                Some(NUMBER_KEY)
            );
            assert!(read_number(&mut map).is_err());
        }
        let mut map = MapDeserializer::<_, Error>::new([(NUMBER_KEY, "0.25")].into_iter());
        assert!(map.next_key::<String>().unwrap().is_some());
        assert!(read_number(&mut map).unwrap().is_number());
    }
}
