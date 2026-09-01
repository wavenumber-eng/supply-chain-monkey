#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! Secure asynchronous client for the Supply Chain Monkey v1 API.
//!
//! The client exposes typed operations backed by TypeSpec-generated contracts.
//! It distinguishes structurally valid provider failures ([`ProviderOutcome`])
//! from transport, HTTP, size-limit, and contract failures ([`ClientError`]).
//! Redirects are disabled, bearer headers are sensitive, response bodies are
//! bounded, and authenticated non-loopback services must use HTTPS.
//!
//! # Quick start
//!
//! ```no_run
//! use scm_client::{ProviderOutcome, ScmClient};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = ScmClient::new(
//!         "https://scm.example.test",
//!         "local-example-token",
//!     )?;
//!
//!     match client.search("lcsc", "RT685").await? {
//!         ProviderOutcome::Response(envelope) => {
//!             let part_count = envelope.data.as_ref().map_or(0, Vec::len);
//!             println!("status={} parts={part_count}", envelope.status);
//!         }
//!         ProviderOutcome::ProviderError(envelope) => {
//!             eprintln!("provider failed: {}", envelope.error.unwrap_or_default());
//!         }
//!     }
//!     Ok(())
//! }
//! ```
//!
//! Use [`ScmClient::builder`] for explicit timeouts, response-size limits,
//! bounded concurrency, proxies, or private certificate authorities. Generated
//! response models and the strict codec are re-exported through [`contracts`].

mod client;
mod config;
mod error;

/// Generated wire models and strict codec used by this client.
pub use scm_contracts as contracts;

pub use client::{
    DEFAULT_SUPPLIERS, LookupOptions, MultiSearchResults, ProviderOutcome, ScmClient, SearchOptions,
};
pub use config::{ClientBuilder, DEFAULT_CONNECT_TIMEOUT, DEFAULT_REQUEST_TIMEOUT};
pub use error::{ClientError, ConfigError, ContractFailure};
