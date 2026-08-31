use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::Router;
use axum::body::{Body, to_bytes};
use axum::extract::{Request, State};
use axum::http::{Method, Response, StatusCode};
use axum::response::Redirect;
use axum::routing::get;
use axum_server::tls_rustls::RustlsConfig;
use rcgen::{CertifiedKey, generate_simple_self_signed};
use scm_client::{
    ClientError, ConfigError, LookupOptions, ProviderOutcome, ScmClient, SearchOptions,
};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
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
    method: Method,
    uri: String,
    authorization: Option<String>,
    body: Vec<u8>,
}

#[derive(Clone, Default)]
struct RecordingState {
    requests: Arc<Mutex<Vec<RecordedRequest>>>,
}

async fn recording_handler(
    State(state): State<RecordingState>,
    request: Request,
) -> Response<Body> {
    let method = request.method().clone();
    let uri = request.uri().to_string();
    let authorization = request
        .headers()
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .map(str::to_owned);
    let path = request.uri().path().to_owned();
    let provider_error = request
        .uri()
        .query()
        .is_some_and(|query| query.contains("supplier=broken"));
    let body = to_bytes(request.into_body(), 1024 * 1024)
        .await
        .expect("request body")
        .to_vec();
    state
        .requests
        .lock()
        .expect("record lock")
        .push(RecordedRequest {
            method,
            uri,
            authorization,
            body,
        });
    let payload = match path.as_str() {
        "/prefix/v1/health" => HEALTH,
        "/prefix/v1/providers/status" => PROVIDERS,
        "/prefix/v1/search" if provider_error => PROVIDER_ERROR,
        "/prefix/v1/search" => SEARCH,
        "/prefix/v1/detail" => DETAIL,
        "/prefix/v1/spn" => SPN,
        "/prefix/v1/spn/batch" => BATCH,
        _ => return status_response(StatusCode::NOT_FOUND, b"not found"),
    };
    status_response(StatusCode::OK, payload)
}

fn status_response(status: StatusCode, payload: &[u8]) -> Response<Body> {
    Response::builder()
        .status(status)
        .header("content-type", "application/json")
        .body(Body::from(payload.to_vec()))
        .expect("test response")
}

async fn spawn_http(app: Router) -> (String, tokio::task::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let address = listener.local_addr().expect("local address");
    let task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("test server");
    });
    (format!("http://{address}"), task)
}

#[test]
fn configuration_enforces_url_token_and_debug_policy() {
    assert!(matches!(
        ScmClient::builder("not a URL"),
        Err(ConfigError::InvalidBaseUrl)
    ));
    assert!(matches!(
        ScmClient::builder("https://user:pass@example.test"),
        Err(ConfigError::BaseUrlCredentials)
    ));
    assert!(matches!(
        ScmClient::builder("https://example.test?mode=bad"),
        Err(ConfigError::BaseUrlQueryOrFragment)
    ));
    assert!(matches!(
        ScmClient::new("http://example.test", "SENSITIVE_MARKER_DO_NOT_LOG"),
        Err(ConfigError::AuthenticatedRemoteHttp)
    ));
    let proxied_loopback = ScmClient::builder("http://127.0.0.1:12345")
        .expect("builder")
        .bearer_token("SENSITIVE_MARKER_DO_NOT_LOG")
        .expect("token")
        .proxy("http://127.0.0.1:23456")
        .expect("proxy")
        .build();
    assert!(matches!(
        proxied_loopback,
        Err(ConfigError::AuthenticatedLoopbackProxy)
    ));
    let client = ScmClient::new("http://127.0.0.1:12345", "SENSITIVE_MARKER_DO_NOT_LOG")
        .expect("loopback HTTP client");
    let diagnostic = format!("{client:?}");
    assert!(!diagnostic.contains("SENSITIVE_MARKER_DO_NOT_LOG"));
    assert!(diagnostic.contains("has_bearer_token: true"));
}

#[tokio::test]
async fn all_supported_operations_use_safe_paths_headers_and_contracts() {
    let state = RecordingState::default();
    let app = Router::new()
        .fallback(recording_handler)
        .with_state(state.clone());
    let (base, task) = spawn_http(app).await;
    let client = ScmClient::new(&format!("{base}/prefix"), "unit-test-credential").expect("client");

    client.health().await.expect("health");
    client.providers_status().await.expect("providers");
    client
        .search_with_options(
            "jlcpcb",
            "A/B + C",
            SearchOptions {
                include_raw: true,
                max_results: 7,
            },
        )
        .await
        .expect("search");
    assert!(matches!(
        client
            .search("broken", "X")
            .await
            .expect("provider envelope"),
        ProviderOutcome::ProviderError(_)
    ));
    client
        .detail_with_options("jlcpcb", "C123", LookupOptions { include_raw: true })
        .await
        .expect("detail");
    client.spn("jlcpcb", "C123").await.expect("spn");
    client
        .spn_batch("jlcpcb", vec!["C123".to_owned(), "C456".to_owned()])
        .await
        .expect("batch");

    {
        let requests = state.requests.lock().expect("record lock");
        assert_eq!(requests.len(), 7);
        assert!(requests[0].authorization.is_none());
        assert!(requests[1..].iter().all(|request| {
            request.authorization.as_deref() == Some("Bearer unit-test-credential")
        }));
        assert!(
            requests
                .iter()
                .all(|request| !request.uri.contains("unit-test-credential"))
        );
        let search = &requests[2];
        assert!(search.uri.contains("mpn=A%2FB+%2B+C"));
        assert!(search.uri.contains("include_raw=true"));
        assert!(search.uri.contains("max_results=7"));
        let batch = requests.last().expect("batch request");
        assert_eq!(batch.method, Method::POST);
        let batch_json: serde_json::Value =
            serde_json::from_slice(&batch.body).expect("batch JSON");
        assert_eq!(batch_json["supplier"], "jlcpcb");
        assert_eq!(batch_json["spns"], serde_json::json!(["C123", "C456"]));
    }
    assert!(matches!(
        client.spn_batch("jlcpcb", Vec::new()).await,
        Err(ClientError::Contract {
            operation: "spn_batch_request",
            ..
        })
    ));
    assert_eq!(state.requests.lock().expect("record lock").len(), 7);
    task.abort();
}

#[tokio::test]
async fn missing_auth_redirect_timeout_and_response_bounds_are_distinct() {
    let final_reached = Arc::new(AtomicBool::new(false));
    let marker = Arc::clone(&final_reached);
    let app = Router::new()
        .route(
            "/v1/health",
            get(|| async { Redirect::temporary("/final") }),
        )
        .route(
            "/final",
            get(move || {
                let marker = Arc::clone(&marker);
                async move {
                    marker.store(true, Ordering::SeqCst);
                    String::from_utf8_lossy(HEALTH).into_owned()
                }
            }),
        );
    let (base, redirect_task) = spawn_http(app).await;
    let client = ScmClient::builder(&base)
        .expect("builder")
        .build()
        .expect("client");
    assert!(matches!(
        client.providers_status().await,
        Err(ClientError::MissingBearerToken)
    ));
    assert!(matches!(
        client.health().await,
        Err(ClientError::Http { status: 307, .. })
    ));
    assert!(!final_reached.load(Ordering::SeqCst));
    redirect_task.abort();

    let large = vec![b'x'; 1024];
    let app = Router::new().route("/v1/health", get(move || async move { large }));
    let (base, bound_task) = spawn_http(app).await;
    let client = ScmClient::builder(&base)
        .expect("builder")
        .max_response_bytes(64)
        .build()
        .expect("client");
    assert!(matches!(
        client.health().await,
        Err(ClientError::ResponseTooLarge { limit: 64, .. })
    ));
    bound_task.abort();

    let app = Router::new().route(
        "/v1/health",
        get(|| async {
            tokio::time::sleep(Duration::from_millis(100)).await;
            String::from_utf8_lossy(HEALTH).into_owned()
        }),
    );
    let (base, timeout_task) = spawn_http(app).await;
    let client = ScmClient::builder(&base)
        .expect("builder")
        .request_timeout(Duration::from_millis(20))
        .build()
        .expect("client");
    assert!(matches!(
        client.health().await,
        Err(ClientError::Transport { .. })
    ));
    timeout_task.abort();

    let app = Router::new().route(
        "/v1/health",
        get(|| async { r#"{"status":"SENSITIVE_MARKER_DO_NOT_LOG"}"# }),
    );
    let (base, contract_task) = spawn_http(app).await;
    let client = ScmClient::builder(&base)
        .expect("builder")
        .build()
        .expect("client");
    let error = client.health().await.expect_err("contract error");
    assert!(matches!(&error, ClientError::Contract { .. }));
    assert!(!format!("{error:?}").contains("SENSITIVE_MARKER_DO_NOT_LOG"));
    contract_task.abort();
}

#[derive(Clone)]
struct ConcurrencyState {
    active: Arc<AtomicUsize>,
    maximum: Arc<AtomicUsize>,
    started: Arc<AtomicUsize>,
    delay_ms: Arc<AtomicU64>,
}

async fn concurrency_handler(State(state): State<ConcurrencyState>) -> Response<Body> {
    let active = state.active.fetch_add(1, Ordering::SeqCst) + 1;
    let _guard = ActiveGuard(Arc::clone(&state.active));
    state.started.fetch_add(1, Ordering::SeqCst);
    state.maximum.fetch_max(active, Ordering::SeqCst);
    let delay = state.delay_ms.load(Ordering::SeqCst);
    tokio::time::sleep(Duration::from_millis(delay)).await;
    status_response(StatusCode::OK, SEARCH)
}

struct ActiveGuard(Arc<AtomicUsize>);

impl Drop for ActiveGuard {
    fn drop(&mut self) {
        self.0.fetch_sub(1, Ordering::SeqCst);
    }
}

#[tokio::test]
async fn multi_search_is_bounded_and_dropping_the_future_stops_scheduling() {
    let state = ConcurrencyState {
        active: Arc::new(AtomicUsize::new(0)),
        maximum: Arc::new(AtomicUsize::new(0)),
        started: Arc::new(AtomicUsize::new(0)),
        delay_ms: Arc::new(AtomicU64::new(30)),
    };
    let app = Router::new()
        .route("/v1/search", get(concurrency_handler))
        .with_state(state.clone());
    let (base, task) = spawn_http(app).await;
    let client = ScmClient::builder(&base)
        .expect("builder")
        .bearer_token("unit-test-credential")
        .expect("token")
        .max_concurrency(2)
        .build()
        .expect("client");
    let suppliers = ["one", "two", "three", "four", "five"];
    let results = client.search_all("X", suppliers).await;
    assert_eq!(results.len(), suppliers.len());
    assert_eq!(state.maximum.load(Ordering::SeqCst), 2);

    state.started.store(0, Ordering::SeqCst);
    state.maximum.store(0, Ordering::SeqCst);
    state.delay_ms.store(200, Ordering::SeqCst);
    let cancelled = tokio::time::timeout(
        Duration::from_millis(20),
        client.search_all("X", ["a", "b", "c", "d"]),
    )
    .await;
    assert!(cancelled.is_err());
    tokio::time::sleep(Duration::from_millis(250)).await;
    assert!(state.started.load(Ordering::SeqCst) <= 2);
    assert_eq!(state.active.load(Ordering::SeqCst), 0);
    task.abort();
}

#[tokio::test]
async fn explicit_proxy_routes_public_requests_without_leaking_credentials() {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("proxy bind");
    let proxy_address = listener.local_addr().expect("proxy address");
    let proxy_task = tokio::spawn(async move {
        let (mut stream, _) = listener.accept().await.expect("proxy accept");
        let mut request = vec![0_u8; 4096];
        let size = stream.read(&mut request).await.expect("proxy read");
        let request = String::from_utf8_lossy(&request[..size]);
        assert!(request.starts_with("GET http://scm.invalid/v1/health HTTP/1.1"));
        assert!(!request.to_ascii_lowercase().contains("authorization:"));
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            HEALTH.len(),
            String::from_utf8_lossy(HEALTH)
        );
        stream
            .write_all(response.as_bytes())
            .await
            .expect("proxy response");
    });
    let client = ScmClient::builder("http://scm.invalid")
        .expect("builder")
        .proxy(&format!("http://{proxy_address}"))
        .expect("proxy")
        .build()
        .expect("client");
    client.health().await.expect("proxied health");
    proxy_task.await.expect("proxy task");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn private_ca_is_rejected_by_default_and_accepted_when_explicitly_merged() {
    let CertifiedKey { cert, signing_key } =
        generate_simple_self_signed(vec!["localhost".to_owned()]).expect("test certificate");
    let certificate_pem = cert.pem();
    let config = RustlsConfig::from_pem(
        certificate_pem.as_bytes().to_vec(),
        signing_key.serialize_pem().into_bytes(),
    )
    .await
    .expect("TLS server config");
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("TLS bind");
    listener
        .set_nonblocking(true)
        .expect("nonblocking TLS listener");
    let address = listener.local_addr().expect("TLS address");
    let app = Router::new().route(
        "/v1/health",
        get(|| async { String::from_utf8_lossy(HEALTH).into_owned() }),
    );
    let task = tokio::spawn(async move {
        axum_server::from_tcp_rustls(listener, config)
            .expect("TLS listener")
            .serve(app.into_make_service())
            .await
            .expect("TLS server");
    });
    let base = format!("https://localhost:{}", address.port());

    let untrusted = ScmClient::builder(&base)
        .expect("builder")
        .request_timeout(Duration::from_secs(2))
        .connect_timeout(Duration::from_secs(2))
        .build()
        .expect("client");
    assert!(matches!(
        untrusted.health().await,
        Err(ClientError::Transport { .. })
    ));

    let trusted = ScmClient::builder(&base)
        .expect("builder")
        .request_timeout(Duration::from_secs(2))
        .connect_timeout(Duration::from_secs(2))
        .add_root_certificates_pem(certificate_pem.as_bytes())
        .expect("private root")
        .build()
        .expect("client");
    trusted.health().await.expect("private-root health");
    task.abort();
}
