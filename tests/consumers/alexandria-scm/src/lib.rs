#![forbid(unsafe_code)]

//! Candidate Alexandria Rust-broker boundary for Supply Chain Monkey.
//!
//! This is a downstream consumption proof, not an Alexandria transport or UI
//! contract. The production integration remains owned by Alexandria's plan.

use std::fmt;
use std::future::Future;

use scm_client::{MultiSearchResults, ScmClient};

/// Secret-bearing configuration retained by the Rust broker.
pub struct BrokerConfig {
    pub service_url: String,
    pub bearer_token: String,
}

/// Failure to construct the broker before any supplier work starts.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BrokerStartError {
    MissingConfiguration,
    InvalidConfiguration,
}

/// Broker-level control-flow failure, separate from SCM's per-provider results.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BrokerSearchError {
    Cancelled,
}

/// Rust-only SCM broker candidate.
pub struct AlexandriaScmBroker {
    client: ScmClient,
}

impl AlexandriaScmBroker {
    /// Build from an application-owned optional configuration record.
    pub fn from_config(config: Option<BrokerConfig>) -> Result<Self, BrokerStartError> {
        let config = config.ok_or(BrokerStartError::MissingConfiguration)?;
        let client = ScmClient::builder(&config.service_url)
            .map_err(|_| BrokerStartError::InvalidConfiguration)?
            .bearer_token(&config.bearer_token)
            .map_err(|_| BrokerStartError::InvalidConfiguration)?
            .max_concurrency(2)
            .build()
            .map_err(|_| BrokerStartError::InvalidConfiguration)?;
        Ok(Self { client })
    }

    /// Search SCM-owned providers concurrently without reclassifying outcomes.
    ///
    /// Dropping this future cancels in-flight client work; no detached provider
    /// tasks are created by this boundary.
    pub async fn search<I, S>(&self, mpn: &str, suppliers: I) -> MultiSearchResults
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.client.search_all(mpn, suppliers).await
    }

    /// Search until the application-owned cancellation signal resolves.
    pub async fn search_until<I, S, F>(
        &self,
        mpn: &str,
        suppliers: I,
        cancelled: F,
    ) -> Result<MultiSearchResults, BrokerSearchError>
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
        F: Future<Output = ()>,
    {
        tokio::pin!(cancelled);
        tokio::select! {
            biased;
            () = &mut cancelled => Err(BrokerSearchError::Cancelled),
            results = self.search(mpn, suppliers) => Ok(results),
        }
    }
}

impl fmt::Debug for AlexandriaScmBroker {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("AlexandriaScmBroker")
            .field("client", &self.client)
            .finish()
    }
}
