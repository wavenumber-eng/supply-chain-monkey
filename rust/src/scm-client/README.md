# supply-chain-monkey-client

Secure asynchronous client for the Supply Chain Monkey v1 API.

## Add the dependency

The crate is not yet on crates.io. Pin the reviewed repository commit and keep
the package alias:

```toml
[dependencies]
scm-client = { package = "supply-chain-monkey-client", git = "https://github.com/wavenumber-eng/supply-chain-monkey.git", rev = "e7bc0587e7a4b6435b993ce982505fb604861d20" }
tokio = { version = "1.53.1", features = ["macros", "rt-multi-thread"] }
```

Use Rust 1.96 or newer; SCM release proofs use the pinned Rust 1.96.1
toolchain. Commit the resolved `Cargo.lock` in the consuming application.

## Search one provider

```rust,no_run
use scm_client::{ProviderOutcome, ScmClient};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let url = std::env::var("SCM_URL")?;
    let token = std::env::var("SCM_TOKEN")?;
    let client = ScmClient::new(&url, &token)?;

    match client.search("lcsc", "RT685").await? {
        ProviderOutcome::Response(envelope) => {
            let count = envelope.data.as_ref().map_or(0, Vec::len);
            println!("received {count} validated parts");
        }
        ProviderOutcome::ProviderError(_) => {
            eprintln!("provider reported a failure");
        }
    }
    Ok(())
}
```

SCM returns provider failures as valid typed envelopes, so they are represented
by `ProviderOutcome::ProviderError`. `ClientError` is reserved for missing
credentials, transport, HTTP, response-size, or strict-contract failures.

## Search several providers

```rust,no_run
# use scm_client::{ProviderOutcome, ScmClient};
# async fn example(client: &ScmClient) {
let results = client
    .search_all("RT685", ["jlcpcb", "lcsc", "digikey", "mouser"])
    .await;

for result in results.into_values() {
    match result {
        Ok(ProviderOutcome::Response(envelope)) => {
            let count = envelope.data.as_ref().map_or(0, Vec::len);
            println!("provider response: {count} parts");
        }
        Ok(ProviderOutcome::ProviderError(_)) => {
            eprintln!("provider reported a failure");
        }
        Err(error) => eprintln!("client failure: {error}"),
    }
}
# }
```

`search_all` keeps one result per supplier in a sorted map and applies the
client's concurrency bound. Use `providers_status` first when the caller wants
to discover only providers configured on a particular server; the proof CLI
implements that workflow.

## Secure builder options

```rust,no_run
use std::time::Duration;
use scm_client::ScmClient;

# fn example(url: &str, token: &str) -> Result<(), Box<dyn std::error::Error>> {
let client = ScmClient::builder(url)?
    .bearer_token(token)?
    .request_timeout(Duration::from_secs(20))
    .connect_timeout(Duration::from_secs(5))
    .max_response_bytes(4 * 1024 * 1024)
    .max_concurrency(4)
    .build()?;
# let _ = client;
# Ok(())
# }
```

The builder also supports an explicit proxy and private PEM roots. The client
uses rustls with platform certificate verification, disables redirects, bounds
response bodies, and marks bearer headers sensitive. Authenticated remote URLs
must use HTTPS; plain HTTP is accepted only for explicit loopback development.
Tokens never belong in URLs, command arguments, logs, errors, or `Debug` output.

Free-form strings in otherwise valid provider envelopes are untrusted. Escape
or normalize manufacturer, part, description, supplier, and error strings
before writing them to terminals, logs, HTML, or another presentation surface.
The `scm` CLI's printable-ASCII table renderer is the hardened reference.

Generated response types and the strict codec are re-exported through
`scm_client::contracts`, so consumers do not need a second direct dependency to
name them. The deprecated query-token event stream is intentionally unsupported.
