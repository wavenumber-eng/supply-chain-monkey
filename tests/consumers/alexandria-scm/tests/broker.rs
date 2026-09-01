use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use alexandria_scm_consumer_proof::{
    AlexandriaScmBroker, BrokerConfig, BrokerSearchError, BrokerStartError,
};
use scm_client::{ClientError, ProviderOutcome};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

const TOKEN: &str = "ALEXANDRIA_SECRET_MARKER_DO_NOT_EXPOSE";
const SEARCH_OK: &str = r#"{"status":"ok","supplier":"SCM","parameter_field_name":"Part #","provider_latency_ms":1,"provider_capabilities":null,"rate_limit":null,"service_timestamp":"2026-08-31T12:34:56Z","cached":false,"data":[{"supplier":"SCM","source_provider":"api","supplier_part_number":"P1","manufacturer":"Example","manufacturer_part_number":"NE555P","description":"Timer","datasheet_url":"https://example.invalid/datasheet","product_url":"https://example.invalid/product","stock_quantity":1,"stock_status":"in_stock","price_breaks":[],"lifecycle_status":"active","packaging":"Tube","extra_data":null}],"error":null,"error_detail":null}"#;
const PROVIDER_ERROR: &str = r#"{"status":"provider_error","supplier":"SCM","parameter_field_name":"Part #","provider_latency_ms":1,"provider_capabilities":null,"rate_limit":null,"service_timestamp":"2026-08-31T12:34:56Z","cached":false,"data":null,"error":"supplier request failed","error_detail":{"code":"upstream_unavailable","retryable":true,"upstream_status_code":503,"upstream_request_id":null}}"#;

#[derive(Clone, Default)]
struct ServerState {
    active: Arc<AtomicUsize>,
    started: Arc<AtomicUsize>,
    requests: Arc<Mutex<Vec<String>>>,
}

struct ActiveGuard(Arc<AtomicUsize>);

impl Drop for ActiveGuard {
    fn drop(&mut self) {
        self.0.fetch_sub(1, Ordering::SeqCst);
    }
}

async fn spawn_server(delay: Duration) -> (String, ServerState, tokio::task::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let address = listener.local_addr().expect("address");
    let state = ServerState::default();
    let server_state = state.clone();
    let task = tokio::spawn(async move {
        loop {
            let Ok((stream, _)) = listener.accept().await else {
                return;
            };
            let request_state = server_state.clone();
            tokio::spawn(async move {
                serve_one(stream, request_state, delay).await;
            });
        }
    });
    (format!("http://{address}"), state, task)
}

async fn serve_one(mut stream: tokio::net::TcpStream, state: ServerState, delay: Duration) {
    state.started.fetch_add(1, Ordering::SeqCst);
    state.active.fetch_add(1, Ordering::SeqCst);
    let _guard = ActiveGuard(Arc::clone(&state.active));
    let mut request = vec![0_u8; 8192];
    let size = stream.read(&mut request).await.expect("read request");
    let request = String::from_utf8_lossy(&request[..size]).into_owned();
    state
        .requests
        .lock()
        .expect("requests")
        .push(request.clone());
    tokio::time::sleep(delay).await;
    let payload = if request.contains("supplier=broken") {
        PROVIDER_ERROR
    } else {
        SEARCH_OK
    };
    let response = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{payload}",
        payload.len()
    );
    stream
        .write_all(response.as_bytes())
        .await
        .expect("write response");
}

fn broker(url: String) -> AlexandriaScmBroker {
    AlexandriaScmBroker::from_config(Some(BrokerConfig {
        service_url: url,
        bearer_token: TOKEN.to_owned(),
    }))
    .expect("broker")
}

#[test]
fn missing_configuration_fails_before_supplier_work() {
    assert_eq!(
        AlexandriaScmBroker::from_config(None).expect_err("missing config"),
        BrokerStartError::MissingConfiguration
    );
}

#[tokio::test]
async fn unreachable_service_is_sanitized_per_supplier() {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("reserve port");
    let url = format!("http://{}", listener.local_addr().expect("address"));
    drop(listener);
    let broker = broker(url);
    let diagnostic = format!("{broker:?}");
    assert!(!diagnostic.contains(TOKEN));

    let results = broker.search("NE555P", ["one", "two"]).await;
    assert_eq!(results.len(), 2);
    assert!(
        results
            .values()
            .all(|result| matches!(result, Err(ClientError::Transport { .. })))
    );
    assert!(!format!("{results:?}").contains(TOKEN));
}

#[tokio::test]
async fn multi_provider_success_and_partial_failure_stay_explicit() {
    let (url, state, task) = spawn_server(Duration::ZERO).await;
    let results = broker(url)
        .search("NE555P", ["digikey", "broken", "mouser"])
        .await;
    assert_eq!(results.len(), 3);
    assert!(matches!(
        results.get("broken"),
        Some(Ok(ProviderOutcome::ProviderError(_)))
    ));
    for supplier in ["digikey", "mouser"] {
        let Some(Ok(ProviderOutcome::Response(envelope))) = results.get(supplier) else {
            panic!("expected successful response for {supplier}");
        };
        assert_eq!(envelope.data.as_ref().map(Vec::len), Some(1));
    }
    assert!(!format!("{results:?}").contains(TOKEN));

    let requests = state.requests.lock().expect("requests");
    assert_eq!(requests.len(), 3);
    assert!(requests.iter().all(|request| {
        request.to_ascii_lowercase().contains(&format!(
            "authorization: bearer {}",
            TOKEN.to_ascii_lowercase()
        )) && !request.lines().next().unwrap_or_default().contains(TOKEN)
    }));
    drop(requests);
    task.abort();
}

#[tokio::test]
async fn dropping_broker_search_cancels_without_scheduling_more_work() {
    let (url, state, task) = spawn_server(Duration::from_millis(200)).await;
    let broker = broker(url);
    let timed = tokio::time::timeout(
        Duration::from_millis(20),
        broker.search("NE555P", ["one", "two", "three", "four"]),
    )
    .await;
    assert!(timed.is_err());
    tokio::time::sleep(Duration::from_millis(250)).await;
    assert!(state.started.load(Ordering::SeqCst) <= 2);
    assert_eq!(state.active.load(Ordering::SeqCst), 0);
    task.abort();
}

#[tokio::test]
async fn pre_signalled_cancellation_starts_no_supplier_work() {
    let (url, state, task) = spawn_server(Duration::from_millis(200)).await;
    let result = broker(url)
        .search_until("NE555P", ["one", "two"], async {})
        .await;
    assert_eq!(result.expect_err("cancelled"), BrokerSearchError::Cancelled);
    tokio::time::sleep(Duration::from_millis(20)).await;
    assert_eq!(state.started.load(Ordering::SeqCst), 0);
    task.abort();
}
