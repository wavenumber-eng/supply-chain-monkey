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
            assert!(decode::<Value>(contract_root, &payload, DEFAULT_MAX_BYTES).is_err());
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
}
