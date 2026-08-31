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

#[derive(Clone, Default)]
struct TestState {
    requests: Arc<Mutex<Vec<RecordedRequest>>>,
}

async fn handler(State(state): State<TestState>, request: Request) -> Response<Body> {
    let uri = request.uri().to_string();
    let path = request.uri().path().to_owned();
    let provider_error = request
        .uri()
        .query()
        .is_some_and(|query| query.contains("supplier=broken"));
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
            uri,
            authorization,
            body,
        });
    let payload = match path.as_str() {
        "/v1/health" => HEALTH,
        "/v1/providers/status" => PROVIDERS,
        "/v1/search" if provider_error => PROVIDER_ERROR,
        "/v1/search" => SEARCH,
        "/v1/detail" => DETAIL,
        "/v1/spn" => SPN,
        "/v1/spn/batch" => BATCH,
        _ => return response(StatusCode::NOT_FOUND, b"not found"),
    };
    response(StatusCode::OK, payload)
}

fn response(status: StatusCode, payload: &[u8]) -> Response<Body> {
    Response::builder()
        .status(status)
        .header("content-type", "application/json")
        .body(Body::from(payload.to_vec()))
        .expect("response")
}

async fn spawn_server() -> (String, TestState, tokio::task::JoinHandle<()>) {
    let state = TestState::default();
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
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn every_supported_command_uses_the_public_client_and_typed_json() {
    let (base, state, task) = spawn_server().await;
    let commands = [
        vec!["health"],
        vec!["providers"],
        vec!["search", "jlcpcb", "A/B", "--include-raw"],
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
    assert_eq!(requests.len(), 6);
    assert!(requests[0].authorization.is_none());
    assert!(requests[1..].iter().all(|request| {
        request.authorization.as_deref() == Some("Bearer CLI_SENSITIVE_MARKER")
            && !request.uri.contains("CLI_SENSITIVE_MARKER")
    }));
    let batch: serde_json::Value = serde_json::from_slice(&requests[5].body).expect("batch body");
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

    let error = invoke(
        vec![
            "--url".to_owned(),
            base,
            "search".to_owned(),
            "broken".to_owned(),
            "X".to_owned(),
        ],
        Some("CLI_SENSITIVE_MARKER"),
    )
    .await;
    assert_eq!(error.status.code(), Some(3));
    assert!(text(&error.stdout).contains("status=provider_error"));
    assert!(!text(&error.stderr).contains("CLI_SENSITIVE_MARKER"));
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
    assert!(text(&directory_error.stderr).contains("not a regular file"));

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
