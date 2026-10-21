use std::fs;
use std::path::{Path, PathBuf};

use scm_contracts::{
    CodecError, ContractRoot, DEFAULT_MAX_BYTES, DetailEnvelope, HealthResponse,
    ProviderStatusResponse, SearchEnvelope, SpnBatchEnvelope, SpnBatchRequest, SpnEnvelope,
    StreamDoneEvent, StreamSearchEvent, decode, encode,
};
use serde::Serialize;
use serde::de::DeserializeOwned;
use serde_json::Value;
use sha2::{Digest, Sha256};

fn vector_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../contracts/scm/v1/vectors")
}

fn manifest() -> Value {
    let bytes = fs::read(vector_root().join("manifest.a0.json")).expect("vector manifest");
    serde_json::from_slice(&bytes).expect("valid vector manifest")
}

fn root_for(name: &str) -> Option<ContractRoot> {
    match name {
        "DetailEnvelope" => Some(ContractRoot::DetailEnvelope),
        "HealthResponse" => Some(ContractRoot::HealthResponse),
        "ProviderStatusResponse" => Some(ContractRoot::ProviderStatusResponse),
        "SearchEnvelope" => Some(ContractRoot::SearchEnvelope),
        "SpnBatchEnvelope" => Some(ContractRoot::SpnBatchEnvelope),
        "SpnBatchRequest" => Some(ContractRoot::SpnBatchRequest),
        "SpnEnvelope" => Some(ContractRoot::SpnEnvelope),
        "StreamDoneEvent" => Some(ContractRoot::StreamDoneEvent),
        "StreamSearchEvent" => Some(ContractRoot::StreamSearchEvent),
        _ => None,
    }
}

fn roundtrip<T>(root: ContractRoot, payload: &[u8])
where
    T: DeserializeOwned + Serialize,
{
    let model: T = decode(root, payload, DEFAULT_MAX_BYTES).expect("decode shared vector");
    let encoded = encode(root, &model, DEFAULT_MAX_BYTES).expect("encode shared vector");
    let _: T = decode(root, &encoded, DEFAULT_MAX_BYTES).expect("decode encoded vector");
}

fn typed_roundtrip(root: ContractRoot, payload: &[u8]) {
    match root {
        ContractRoot::DetailEnvelope => roundtrip::<DetailEnvelope>(root, payload),
        ContractRoot::HealthResponse => roundtrip::<HealthResponse>(root, payload),
        ContractRoot::ProviderStatusResponse => roundtrip::<ProviderStatusResponse>(root, payload),
        ContractRoot::SearchEnvelope => roundtrip::<SearchEnvelope>(root, payload),
        ContractRoot::SpnBatchEnvelope => roundtrip::<SpnBatchEnvelope>(root, payload),
        ContractRoot::SpnBatchRequest => roundtrip::<SpnBatchRequest>(root, payload),
        ContractRoot::SpnEnvelope => roundtrip::<SpnEnvelope>(root, payload),
        ContractRoot::StreamDoneEvent => roundtrip::<StreamDoneEvent>(root, payload),
        ContractRoot::StreamSearchEvent => roundtrip::<StreamSearchEvent>(root, payload),
    }
}

fn vector_bytes(root: &Path, case: &Value) -> Vec<u8> {
    fs::read(root.join(case["path"].as_str().expect("case path"))).expect("vector payload")
}

#[test]
fn shared_vectors_match_digests_and_contract_outcomes() {
    let root = vector_root();
    for case in manifest()["cases"].as_array().expect("manifest cases") {
        let payload = vector_bytes(&root, case);
        let digest = Sha256::digest(&payload)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>();
        assert_eq!(digest, case["sha256"].as_str().expect("case digest"));
        let Some(contract_root) = root_for(case["schema"].as_str().expect("case schema")) else {
            continue;
        };
        if case["valid"].as_bool() == Some(true) {
            typed_roundtrip(contract_root, &payload);
        } else {
            let error = decode::<Value>(contract_root, &payload, DEFAULT_MAX_BYTES)
                .expect_err("invalid shared vector must fail");
            let failure = case["failure"].as_str().expect("invalid failure class");
            match failure {
                "duplicate_member" | "nonfinite" | "unsafe_integer" => {
                    assert!(matches!(error, CodecError::Json(_)), "{failure}: {error}");
                }
                "schema" => {
                    assert!(matches!(error, CodecError::Schema(_)), "{failure}: {error}");
                }
                other => panic!("unknown shared-vector failure class: {other}"),
            }
        }
    }
}

#[test]
fn generated_roots_have_vectors_and_reject_unknown_fields() {
    let document = manifest();
    let cases = document["cases"].as_array().expect("manifest cases");
    for root in ContractRoot::ALL {
        assert!(cases.iter().any(|case| {
            case["valid"].as_bool() == Some(true)
                && root_for(case["schema"].as_str().unwrap_or_default()) == Some(*root)
        }));
    }
    assert!(serde_json::from_slice::<HealthResponse>(br#"{"status":"ok","extra":true}"#).is_err());
}

#[test]
fn codec_enforces_bounds_and_duplicate_preflight() {
    let health = br#"{"status":"ok"}"#;
    assert!(matches!(
        decode::<HealthResponse>(ContractRoot::HealthResponse, health, health.len() - 1),
        Err(CodecError::PayloadTooLarge { .. })
    ));
    let duplicate = br#"{"status":"ok","status":"ok"}"#;
    assert!(matches!(
        decode::<HealthResponse>(ContractRoot::HealthResponse, duplicate, DEFAULT_MAX_BYTES),
        Err(CodecError::Json(_))
    ));

    let malformed_utf8 = b"{\"status\":\"\xff\"}";
    assert!(matches!(
        decode::<HealthResponse>(
            ContractRoot::HealthResponse,
            malformed_utf8,
            DEFAULT_MAX_BYTES
        ),
        Err(CodecError::Json(_))
    ));

    let unpaired_surrogate = br#"{"status":"\ud800"}"#;
    assert!(matches!(
        decode::<HealthResponse>(
            ContractRoot::HealthResponse,
            unpaired_surrogate,
            DEFAULT_MAX_BYTES
        ),
        Err(CodecError::Json(_))
    ));
}

#[test]
fn optional_batch_boolean_uses_typespec_default() {
    let omitted = br#"{"supplier":"LCSC","spns":["C123"]}"#;
    let request: SpnBatchRequest =
        decode(ContractRoot::SpnBatchRequest, omitted, DEFAULT_MAX_BYTES)
            .expect("omitted include_raw uses the TypeSpec default");
    assert!(!request.include_raw);
}

// Insert an exact authored JSON fragment in an existing open provider-data bucket.
// Text insertion preserves the number lexeme that the strict boundary must inspect.
fn search_with_extra(extra: &str) -> Vec<u8> {
    let bytes = fs::read(vector_root().join("valid/search-ok.json")).expect("search fixture");
    let mut value: Value = serde_json::from_slice(&bytes).expect("fixture JSON");
    value["data"][0]["extra_data"] = Value::String("SCM_RAW_EXTRA_FRAGMENT".into());
    serde_json::to_string(&value)
        .expect("fixture encoding")
        .replace("\"SCM_RAW_EXTRA_FRAGMENT\"", extra)
        .into_bytes()
}

#[test]
fn numeric_values_keep_finite_float_and_safe_integer_semantics() {
    for literal in [
        "0.0",
        "-0.0",
        "0.1",
        "0.10000000000000001",
        "1.25",
        "1.25e-3",
        "1e3",
        "1e20",
        "-0",
        "9007199254740991",
        "-9007199254740991",
    ] {
        let payload = search_with_extra(&format!(r#"{{"nested":[{{"number":{literal}}}]}}"#));
        let model: SearchEnvelope =
            decode(ContractRoot::SearchEnvelope, &payload, DEFAULT_MAX_BYTES)
                .unwrap_or_else(|error| panic!("finite/safe {literal}: {error}"));
        let actual = serde_json::to_value(&model).expect("typed numeric projection");
        let actual = &actual["data"][0]["extra_data"]["nested"][0]["number"];
        assert!(
            actual.is_number(),
            "number must not become an untagged map: {literal}"
        );
        assert_eq!(actual.as_f64(), Some(literal.parse::<f64>().unwrap()));
        let encoded = encode(ContractRoot::SearchEnvelope, &model, DEFAULT_MAX_BYTES)
            .expect("encode safe number");
        decode::<SearchEnvelope>(ContractRoot::SearchEnvelope, &encoded, DEFAULT_MAX_BYTES)
            .expect("decode encoded safe number");
    }
    for literal in [
        "9007199254740992",
        "-9007199254740992",
        "1e999",
        "NaN",
        "Infinity",
    ] {
        let payload = search_with_extra(&format!(r#"{{"number":{literal}}}"#));
        assert!(
            matches!(
                decode::<SearchEnvelope>(ContractRoot::SearchEnvelope, &payload, DEFAULT_MAX_BYTES),
                Err(CodecError::Json(_))
            ),
            "invalid {literal}"
        );
    }
}

#[test]
fn duplicates_stay_rejected_after_first_key_and_inside_nested_float_objects() {
    for extra in [
        r#"{"a":0.0,"a":1.0}"#,
        r#"{"nested":[{"a":0.0,"b":1,"a":2}]}"#,
    ] {
        let payload = search_with_extra(extra);
        assert!(matches!(
            decode::<SearchEnvelope>(ContractRoot::SearchEnvelope, &payload, DEFAULT_MAX_BYTES),
            Err(CodecError::Json(_))
        ));
    }
}

#[cfg(feature = "serde-json-arbitrary-precision")]
#[test]
fn arbitrary_precision_rejects_integer_lexemes_beyond_machine_integer_ranges() {
    for literal in [
        "18446744073709551616".to_owned(),
        "-18446744073709551616".to_owned(),
        "1".to_owned() + &"0".repeat(100),
    ] {
        let payload = search_with_extra(&format!(r#"{{"number":{literal}}}"#));
        assert!(
            matches!(
                decode::<SearchEnvelope>(ContractRoot::SearchEnvelope, &payload, DEFAULT_MAX_BYTES),
                Err(CodecError::Json(_))
            ),
            "wide integer {literal}"
        );
    }
}

#[cfg(feature = "serde-json-arbitrary-precision")]
#[test]
fn arbitrary_precision_refuses_authored_number_key_spoofs_without_rejecting_string_values() {
    for extra in [
        r#"{"$serde_json::private::Number":"0.25"}"#,
        r#"{"\u0024serde_json::private::Number":"0.25"}"#,
        r#"{"other":true,"$serde_json::private::Number":"0.25"}"#,
        r#"{"nested":[{"$serde_json::private::Number":"NaN"}]}"#,
        r#"{"$serde_json::private::Number":"0.25","tail":true}"#,
    ] {
        assert!(matches!(
            decode::<SearchEnvelope>(
                ContractRoot::SearchEnvelope,
                &search_with_extra(extra),
                DEFAULT_MAX_BYTES
            ),
            Err(CodecError::Json(_))
        ));
    }
    for extra in [
        r#"{"note":"$serde_json::private::Number"}"#,
        r#"{"\u0024ordinary":"0.25"}"#,
        r#"{"note":"\"$serde_json::private::Number\":\"0.25\""}"#,
    ] {
        decode::<SearchEnvelope>(
            ContractRoot::SearchEnvelope,
            &search_with_extra(extra),
            DEFAULT_MAX_BYTES,
        )
        .expect("ordinary strings are not synthetic number keys");
    }
}

#[cfg(feature = "serde-json-arbitrary-precision")]
#[test]
fn arbitrary_precision_encode_applies_the_same_reserved_key_and_integer_limits() {
    let mut value: Value = serde_json::from_slice(&search_with_extra(r#"{"value":1}"#)).unwrap();
    value["data"][0]["extra_data"] = serde_json::json!({"$serde_json::private::Number":"0.25"});
    assert!(value["data"][0]["extra_data"].is_object());
    assert!(matches!(
        encode(ContractRoot::SearchEnvelope, &value, DEFAULT_MAX_BYTES),
        Err(CodecError::Json(_))
    ));
    value["data"][0]["extra_data"] = serde_json::json!({"value":"placeholder"});
    value["data"][0]["extra_data"]["value"] =
        Value::Number("18446744073709551616".parse().unwrap());
    assert!(matches!(
        encode(ContractRoot::SearchEnvelope, &value, DEFAULT_MAX_BYTES),
        Err(CodecError::Json(_))
    ));
}

#[cfg(not(feature = "serde-json-arbitrary-precision"))]
#[test]
fn feature_off_preserves_existing_literal_keys_and_wide_integer_float_fallback() {
    // This records the existing feature-off limitation, not a safe-integer claim.
    for extra in [
        r#"{"$serde_json::private::Number":"0.25"}"#,
        r#"{"number":18446744073709551616}"#,
    ] {
        decode::<SearchEnvelope>(
            ContractRoot::SearchEnvelope,
            &search_with_extra(extra),
            DEFAULT_MAX_BYTES,
        )
        .expect("feature-off compatibility remains unchanged");
    }
}
