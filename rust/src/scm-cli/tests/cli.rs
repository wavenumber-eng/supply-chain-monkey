use std::process::{Command, Output};
use std::sync::{Arc, Mutex};

use axum::Router;
use axum::body::{Body, to_bytes};
use axum::extract::{Request, State};
use axum::http::{Response, StatusCode};
use tokio::net::TcpListener;

const HEALTH: &[u8] = include_bytes!("../../../../contracts/scm/v1/vectors/valid/health.json");
const PROVIDERS: &[u8] =
    include_bytes!("../../../../contracts/scm/v1/vectors/valid/provider-status.json");
const SEARCH: &[u8] = include_bytes!("../../../../contracts/scm/v1/vectors/valid/search-ok.json");
const PROVIDER_ERROR: &[u8] =
    include_bytes!("../../../../contracts/scm/v1/vectors/valid/search-provider-error.json");
const NOT_FOUND: &[u8] =
    include_bytes!("../../../../contracts/scm/v1/vectors/valid/search-not-found.json");
const EMPTY_PROVIDERS: &[u8] = br#"{"providers":{}}"#;
const MALICIOUS_PROVIDER: &str = "bad\u{1b}\u{7}Ω";
const DETAIL: &[u8] = include_bytes!("../../../../contracts/scm/v1/vectors/valid/detail-ok.json");
const SPN: &[u8] = include_bytes!("../../../../contracts/scm/v1/vectors/valid/spn-ok.json");
const BATCH: &[u8] =
    include_bytes!("../../../../contracts/scm/v1/vectors/valid/spn-batch-partial.json");

#[derive(Clone, Debug)]
struct RecordedRequest {
    uri: String,
    authorization: Option<String>,
    body: Vec<u8>,
}

#[derive(Clone)]
struct TestState {
    requests: Arc<Mutex<Vec<RecordedRequest>>>,
    providers: Arc<Vec<u8>>,
}

impl TestState {
    fn new(providers: &[u8]) -> Self {
        Self {
            requests: Arc::default(),
            providers: Arc::new(providers.to_vec()),
        }
    }
}

async fn handler(State(state): State<TestState>, request: Request) -> Response<Body> {
    let uri = request.uri().to_string();
    let path = request.uri().path().to_owned();
    let authorization = request
        .headers()
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .map(str::to_owned);
    let body = to_bytes(request.into_body(), 1024 * 1024)
        .await
        .expect("request body")
        .to_vec();
    state
        .requests
        .lock()
        .expect("record lock")
        .push(RecordedRequest {
            uri: uri.clone(),
            authorization,
            body,
        });
    let payload = match path.as_str() {
        "/v1/health" => HEALTH.to_vec(),
        "/v1/providers/status" => state.providers.as_ref().clone(),
        "/v1/search" => search_payload(&uri),
        "/v1/detail" => DETAIL.to_vec(),
        "/v1/spn" => SPN.to_vec(),
        "/v1/spn/batch" => BATCH.to_vec(),
        _ => return response(StatusCode::NOT_FOUND, b"not found"),
    };
    response(StatusCode::OK, &payload)
}

fn requested_supplier(uri: &str) -> Option<&str> {
    uri.split('?')
        .nth(1)?
        .split('&')
        .find_map(|item| item.strip_prefix("supplier="))
}

fn search_payload(uri: &str) -> Vec<u8> {
    let supplier = requested_supplier(uri).unwrap_or_default();
    if uri.contains("%1B") || uri.contains("%1b") {
        return NOT_FOUND.to_vec();
    }
    if supplier == "broken" {
        return PROVIDER_ERROR.to_vec();
    }
    if supplier == "invalid" {
        return b"{}".to_vec();
    }
    if supplier == "notfound" {
        return NOT_FOUND.to_vec();
    }
    let mut value: serde_json::Value = serde_json::from_slice(SEARCH).expect("search fixture");
    let part = &mut value["data"][0];
    part["supplier"] = serde_json::json!(supplier);
    match supplier {
        "long" => {
            part["manufacturer"] = serde_json::json!("\u{1b}\u{7}Mégacorp with extra words");
            part["description"] =
                serde_json::json!("A long\tdescription Ω that must be truncated safely");
            part["price_breaks"] = serde_json::json!([]);
        }
        "high" => part["stock_quantity"] = serde_json::json!(2_000),
        "low" => part["stock_quantity"] = serde_json::json!(10),
        "equal-a" | "equal-b" => part["stock_quantity"] = serde_json::json!(100),
        "tiny-price" => part["price_breaks"][0]["unit_price"] = serde_json::json!(0.0001),
        "large-price" => part["price_breaks"][0]["unit_price"] = serde_json::json!(123_456_789.25),
        _ => {}
    }
    serde_json::to_vec(&value).expect("search fixture mutation")
}

fn providers_payload(names: &[&str]) -> Vec<u8> {
    let source: serde_json::Value = serde_json::from_slice(PROVIDERS).expect("provider fixture");
    let template = source["providers"]["LCSC"].clone();
    let providers = names
        .iter()
        .map(|name| {
            let mut entry = template.clone();
            entry["configured"] = serde_json::json!(true);
            entry["capabilities"]["supplier"] = serde_json::json!(name);
            ((*name).to_owned(), entry)
        })
        .collect::<serde_json::Map<_, _>>();
    serde_json::to_vec(&serde_json::json!({"providers": providers})).expect("providers fixture")
}

fn malicious_providers_payload() -> Vec<u8> {
    let payload = providers_payload(&[MALICIOUS_PROVIDER]);
    let mut value: serde_json::Value = serde_json::from_slice(&payload).expect("providers fixture");
    value["providers"][MALICIOUS_PROVIDER]["backend"] = serde_json::json!("api\u{1b}\u{7}Ω");
    serde_json::to_vec(&value).expect("malicious providers fixture")
}

fn response(status: StatusCode, payload: &[u8]) -> Response<Body> {
    Response::builder()
        .status(status)
        .header("content-type", "application/json")
        .body(Body::from(payload.to_vec()))
        .expect("response")
}

async fn spawn_server() -> (String, TestState, tokio::task::JoinHandle<()>) {
    spawn_server_with_providers(PROVIDERS).await
}

async fn spawn_server_with_providers(
    providers: &[u8],
) -> (String, TestState, tokio::task::JoinHandle<()>) {
    let state = TestState::new(providers);
    let app = Router::new().fallback(handler).with_state(state.clone());
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let address = listener.local_addr().expect("address");
    let task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("server");
    });
    (format!("http://{address}"), state, task)
}

async fn invoke(arguments: Vec<String>, token: Option<&str>) -> Output {
    let token = token.map(str::to_owned);
    tokio::task::spawn_blocking(move || {
        let mut command = Command::new(env!("CARGO_BIN_EXE_scm"));
        command.args(arguments).env_remove("SCM_TOKEN");
        if let Some(token) = token {
            command.env("SCM_TOKEN", token);
        }
        command.output().expect("run scm")
    })
    .await
    .expect("CLI task")
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8(bytes.to_vec()).expect("UTF-8 CLI output")
}

#[tokio::test]
async fn help_has_no_token_argument_and_missing_token_is_sanitized() {
    let help = invoke(vec!["--help".to_owned()], None).await;
    assert!(help.status.success());
    let help = text(&help.stdout);
    assert!(help.contains("SCM_TOKEN"));
    assert!(!help.contains("--token"));

    let search_help = invoke(vec!["search".to_owned(), "--help".to_owned()], None).await;
    assert!(search_help.status.success());
    let search_help = text(&search_help.stdout);
    assert!(search_help.contains("search [OPTIONS] <MPN>"));
    assert!(search_help.contains("--supplier <NAME>"));

    let missing = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "providers".to_owned(),
        ],
        None,
    )
    .await;
    assert_eq!(missing.status.code(), Some(1));
    assert!(text(&missing.stderr).contains("SCM_TOKEN is required"));

    let usage = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "search".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(usage.status.code(), Some(2));

    let empty_supplier = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "search".to_owned(),
            "RT685".to_owned(),
            "--supplier".to_owned(),
            "   ".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(empty_supplier.status.code(), Some(2));
    assert!(text(&empty_supplier.stderr).contains("supplier name must not be empty"));

    let retired_positional = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "search".to_owned(),
            "LCSC".to_owned(),
            "RT685".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(retired_positional.status.code(), Some(2));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn every_supported_command_uses_the_public_client_and_typed_json() {
    let (base, state, task) = spawn_server().await;
    let commands = [
        vec!["health"],
        vec!["providers"],
        vec!["search", "A/B", "--include-raw"],
        vec!["detail", "jlcpcb", "C123"],
        vec!["spn", "jlcpcb", "C123"],
        vec!["batch", "jlcpcb", "C123", "C456"],
    ];
    for command in commands {
        let token = (command[0] != "health").then_some("CLI_SENSITIVE_MARKER");
        let mut arguments = vec!["--url".to_owned(), base.clone(), "--json".to_owned()];
        arguments.extend(command.into_iter().map(str::to_owned));
        assert!(
            arguments
                .iter()
                .all(|value| value != "CLI_SENSITIVE_MARKER")
        );
        let output = invoke(arguments, token).await;
        assert!(output.status.success(), "{}", text(&output.stderr));
        let value: serde_json::Value = serde_json::from_slice(&output.stdout).expect("JSON");
        assert!(value.is_object());
        assert!(!text(&output.stdout).contains("CLI_SENSITIVE_MARKER"));
        assert!(!text(&output.stderr).contains("CLI_SENSITIVE_MARKER"));
    }
    let requests = state.requests.lock().expect("record lock");
    assert_eq!(requests.len(), 8);
    assert!(requests[0].authorization.is_none());
    assert!(requests[1..].iter().all(|request| {
        request.authorization.as_deref() == Some("Bearer CLI_SENSITIVE_MARKER")
            && !request.uri.contains("CLI_SENSITIVE_MARKER")
    }));
    let search_requests = requests
        .iter()
        .filter(|request| request.uri.starts_with("/v1/search?"))
        .collect::<Vec<_>>();
    assert_eq!(search_requests.len(), 2);
    assert!(
        search_requests
            .iter()
            .any(|request| request.uri.contains("supplier=jlcpcb"))
    );
    assert!(
        search_requests
            .iter()
            .any(|request| request.uri.contains("supplier=lcsc"))
    );
    assert!(search_requests.iter().all(|request| {
        !request.uri.contains("supplier=digikey") && !request.uri.contains("supplier=mouser")
    }));
    let batch_request = requests
        .iter()
        .find(|request| request.uri == "/v1/spn/batch")
        .expect("batch request");
    let batch: serde_json::Value = serde_json::from_slice(&batch_request.body).expect("batch body");
    assert_eq!(batch["spns"], serde_json::json!(["C123", "C456"]));
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn human_output_is_stable_and_provider_errors_have_exit_three() {
    let (base, _, task) = spawn_server().await;
    let providers = invoke(
        vec!["--url".to_owned(), base.clone(), "providers".to_owned()],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(providers.status.success());
    let providers = text(&providers.stdout);
    let digikey = providers.find("Digikey").expect("Digikey");
    let jlcpcb = providers.find("JLCPCB").expect("JLCPCB");
    let lcsc = providers.find("LCSC").expect("LCSC");
    let mouser = providers.find("Mouser").expect("Mouser");
    assert!(digikey < jlcpcb && jlcpcb < lcsc && lcsc < mouser);

    let table = invoke(
        vec![
            "--url".to_owned(),
            base.clone(),
            "search".to_owned(),
            "NE555P".to_owned(),
            "--supplier".to_owned(),
            "lcsc".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(table.status.success(), "{}", text(&table.stderr));
    let table = text(&table.stdout);
    for heading in [
        "Supplier",
        "Manufacturer",
        "MPN",
        "Supplier PN",
        "Description",
        "Price",
        "Stock",
    ] {
        assert!(table.contains(heading));
    }
    assert!(table.contains("Texas Ins..."));
    assert!(table.contains("NE555P"));
    assert!(table.contains("296-6501-1-ND"));
    assert!(table.contains("USD 0.42 @ 1"));
    assert!(table.contains("1,250"));
    assert!(table.is_ascii());

    let error_providers = providers_payload(&["broken"]);
    let (error_base, _, error_task) = spawn_server_with_providers(&error_providers).await;
    let error = invoke(
        vec![
            "--url".to_owned(),
            error_base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "broken".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(error.status.code(), Some(3));
    assert!(text(&error.stdout).contains("broken: provider_error"));
    assert!(!text(&error.stderr).contains("CLI_SENSITIVE_MARKER"));
    error_task.abort();
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn human_output_escapes_provider_metadata_and_status_labels() {
    let providers = malicious_providers_payload();
    let (base, _, task) = spawn_server_with_providers(&providers).await;

    let status = invoke(
        vec!["--url".to_owned(), base.clone(), "providers".to_owned()],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(status.status.success(), "{}", text(&status.stderr));
    let status = text(&status.stdout);
    assert!(status.contains(r"bad\x1B\x07\u{3A9}"));
    assert!(status.contains(r"backend=api\x1B\x07\u{3A9}"));
    assert!(status.is_ascii());

    let search = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(search.status.success(), "{}", text(&search.stderr));
    let search = text(&search.stdout);
    assert!(search.contains(r"bad\x1B\x07\u{3A9}: not_found"));
    assert!(search.is_ascii());
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn supplier_filters_dedupe_and_mixed_failures_remain_visible() {
    let providers = providers_payload(&["lcsc", "jlcpcb", "invalid", "broken"]);
    let (base, state, task) = spawn_server_with_providers(&providers).await;
    let duplicate = invoke(
        vec![
            "--url".to_owned(),
            base.clone(),
            "--json".to_owned(),
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "LCSC".to_owned(),
            "--supplier".to_owned(),
            "lcsc".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(duplicate.status.success(), "{}", text(&duplicate.stderr));
    let document: serde_json::Value =
        serde_json::from_slice(&duplicate.stdout).expect("search JSON");
    assert_eq!(document["query"], "X");
    assert_eq!(
        document["providers"].as_object().expect("providers").len(),
        1
    );
    assert_eq!(document["providers"]["lcsc"]["outcome"], "response");

    let mixed = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "jlcpcb".to_owned(),
            "--supplier".to_owned(),
            "invalid".to_owned(),
            "--supplier".to_owned(),
            "broken".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(mixed.status.code(), Some(1));
    assert!(text(&mixed.stdout).contains("client_error"));
    assert!(text(&mixed.stdout).contains("provider_error"));
    assert!(text(&mixed.stdout).contains("NE555P"));
    assert!(!text(&mixed.stderr).contains("CLI_SENSITIVE_MARKER"));

    let requests = state.requests.lock().expect("record lock");
    let lcsc_requests = requests
        .iter()
        .filter(|request| request.uri.contains("supplier=lcsc"))
        .count();
    assert_eq!(lcsc_requests, 1);
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn table_normalizes_truncates_and_handles_absent_prices() {
    let providers = providers_payload(&["long"]);
    let (base, _, task) = spawn_server_with_providers(&providers).await;
    let output = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "long".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(output.status.success(), "{}", text(&output.stderr));
    let output = text(&output.stdout);
    assert!(output.contains("\\x1B\\x07M..."));
    assert!(output.lines().any(|line| line.contains("| -")));
    assert!(!output.contains('\t'));
    assert!(!output.contains('\u{1b}'));
    assert!(!output.contains('\u{7}'));
    assert!(output.is_ascii());
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn generic_search_fails_cleanly_when_no_provider_is_configured() {
    let (base, _, task) = spawn_server_with_providers(EMPTY_PROVIDERS).await;
    let output = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(output.status.code(), Some(1));
    assert!(text(&output.stderr).contains("no configured search providers"));
    assert!(!text(&output.stderr).contains("CLI_SENSITIVE_MARKER"));
    task.abort();

    let (base, _, task) = spawn_server_with_providers(EMPTY_PROVIDERS).await;
    let explicit = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "lcsc".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(explicit.status.code(), Some(1));
    assert!(text(&explicit.stderr).contains("no configured search providers"));
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn explicit_unconfigured_provider_is_rejected_before_search() {
    let (base, state, task) = spawn_server().await;
    let output = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "digikey".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(output.status.code(), Some(1));
    assert!(text(&output.stderr).contains("not configured: digikey"));
    let requests = state.requests.lock().expect("record lock");
    assert_eq!(requests.len(), 1);
    assert_eq!(requests[0].uri, "/v1/providers/status");
    task.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn not_found_is_success_and_rows_sort_by_stock_then_identity() {
    let providers = providers_payload(&["notfound", "low", "equal-b", "equal-a", "high"]);
    let (base, _, task) = spawn_server_with_providers(&providers).await;
    let not_found = invoke(
        vec![
            "--url".to_owned(),
            base.clone(),
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "notfound".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(not_found.status.success());
    assert!(text(&not_found.stdout).contains("notfound: not_found"));

    let sorted = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "X".to_owned(),
            "--supplier".to_owned(),
            "low".to_owned(),
            "--supplier".to_owned(),
            "equal-b".to_owned(),
            "--supplier".to_owned(),
            "equal-a".to_owned(),
            "--supplier".to_owned(),
            "high".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert!(sorted.status.success(), "{}", text(&sorted.stderr));
    let sorted = text(&sorted.stdout);
    let high = sorted.find("high").expect("high row");
    let equal_a = sorted.find("equal-a").expect("equal-a row");
    let equal_b = sorted.find("equal-b").expect("equal-b row");
    let low = sorted.find("low").expect("low row");
    assert!(high < equal_a && equal_a < equal_b && equal_b < low);
    task.abort();
}

#[tokio::test]
async fn ca_bundle_input_is_regular_and_bounded() {
    let directory = std::env::temp_dir();
    let directory_error = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "--ca-bundle".to_owned(),
            directory.display().to_string(),
            "health".to_owned(),
        ],
        None,
    )
    .await;
    assert_eq!(directory_error.status.code(), Some(1));
    let directory_stderr = text(&directory_error.stderr);
    assert!(
        directory_stderr.contains("not a regular file")
            || directory_stderr.contains("could not read the configured CA bundle")
    );

    let path = std::env::temp_dir().join(format!(
        "scm-cli-oversized-ca-{}-{}.pem",
        std::process::id(),
        std::thread::current().name().unwrap_or("test")
    ));
    std::fs::write(&path, vec![b'x'; 1024 * 1024 + 1]).expect("oversized CA fixture");
    let oversized = invoke(
        vec![
            "--url".to_owned(),
            "http://127.0.0.1:1".to_owned(),
            "--ca-bundle".to_owned(),
            path.display().to_string(),
            "health".to_owned(),
        ],
        None,
    )
    .await;
    std::fs::remove_file(path).expect("remove oversized CA fixture");
    assert_eq!(oversized.status.code(), Some(1));
    assert!(text(&oversized.stderr).contains("exceeds the 1 MiB limit"));
}
