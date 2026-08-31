//! Typed SCM operations over the secured transport.

use std::collections::BTreeMap;
use std::fmt;
use std::sync::Arc;

use futures_util::stream::{self, StreamExt};
use reqwest::header::{AUTHORIZATION, CONTENT_TYPE, HeaderValue};
use reqwest::{Method, RequestBuilder, Response, Url};
use scm_contracts::{
    ContractRoot, DetailEnvelope, HealthResponse, ProviderStatusResponse, SearchEnvelope,
    SpnBatchEnvelope, SpnBatchRequest, SpnEnvelope, decode, encode,
};
use serde::Serialize;
use serde::de::DeserializeOwned;

use crate::{ClientBuilder, ClientError, ConfigError, ContractFailure};

/// Suppliers supported by the current deployed SCM v1 service.
pub const DEFAULT_SUPPLIERS: &[&str] = &["jlcpcb", "lcsc", "digikey", "mouser"];

/// Query options shared by detail and exact-SPN lookups.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize)]
pub struct LookupOptions {
    /// Include provider-owned flexible raw data.
    pub include_raw: bool,
}

/// Query options for manufacturer-part-number search.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub struct SearchOptions {
    /// Include provider-owned flexible raw data.
    pub include_raw: bool,
    /// Maximum results requested from one provider.
    pub max_results: u32,
}

impl Default for SearchOptions {
    fn default() -> Self {
        Self {
            include_raw: false,
            max_results: 10,
        }
    }
}

/// A structurally valid SCM envelope, with provider failures kept explicit.
#[derive(Clone, Debug)]
pub enum ProviderOutcome<T> {
    /// An `ok`, `not_found`, or `partial` envelope.
    Response(T),
    /// A `provider_error` envelope, distinct from client infrastructure errors.
    ProviderError(T),
}

impl<T> ProviderOutcome<T> {
    /// Borrow the underlying generated envelope.
    pub const fn envelope(&self) -> &T {
        match self {
            Self::Response(value) | Self::ProviderError(value) => value,
        }
    }

    /// Consume the outcome and return its generated envelope.
    pub fn into_envelope(self) -> T {
        match self {
            Self::Response(value) | Self::ProviderError(value) => value,
        }
    }

    fn classify(value: T, provider_error: bool) -> Self {
        if provider_error {
            Self::ProviderError(value)
        } else {
            Self::Response(value)
        }
    }
}

/// Per-supplier results from a bounded concurrent search.
pub type MultiSearchResults =
    BTreeMap<String, Result<ProviderOutcome<SearchEnvelope>, ClientError>>;

/// Reusable asynchronous SCM API client.
#[derive(Clone)]
pub struct ScmClient {
    transport: reqwest::Client,
    base_url: Url,
    bearer_token: Option<HeaderValue>,
    max_response_bytes: usize,
    max_concurrency: usize,
}

impl ScmClient {
    /// Begin configuring a client for a service base URL.
    pub fn builder(base_url: &str) -> Result<ClientBuilder, ConfigError> {
        ClientBuilder::new(base_url)
    }

    /// Construct a client with a bearer token and secure defaults.
    pub fn new(base_url: &str, bearer_token: &str) -> Result<Self, ConfigError> {
        Self::builder(base_url)?.bearer_token(bearer_token)?.build()
    }

    pub(crate) fn from_parts(
        transport: reqwest::Client,
        base_url: Url,
        bearer_token: Option<HeaderValue>,
        max_response_bytes: usize,
        max_concurrency: usize,
    ) -> Self {
        Self {
            transport,
            base_url,
            bearer_token,
            max_response_bytes,
            max_concurrency,
        }
    }

    /// Read the public health endpoint.
    pub async fn health(&self) -> Result<HealthResponse, ClientError> {
        let request = self.public_request("health", Method::GET, "v1/health")?;
        self.execute("health", ContractRoot::HealthResponse, request)
            .await
    }

    /// Read provider configuration and capability status.
    pub async fn providers_status(&self) -> Result<ProviderStatusResponse, ClientError> {
        let request =
            self.authenticated_request("providers_status", Method::GET, "v1/providers/status")?;
        self.execute(
            "providers_status",
            ContractRoot::ProviderStatusResponse,
            request,
        )
        .await
    }

    /// Search one supplier with default options.
    pub async fn search(
        &self,
        supplier: &str,
        mpn: &str,
    ) -> Result<ProviderOutcome<SearchEnvelope>, ClientError> {
        self.search_with_options(supplier, mpn, SearchOptions::default())
            .await
    }

    /// Search one supplier with explicit raw-data and result-count options.
    pub async fn search_with_options(
        &self,
        supplier: &str,
        mpn: &str,
        options: SearchOptions,
    ) -> Result<ProviderOutcome<SearchEnvelope>, ClientError> {
        #[derive(Serialize)]
        struct Query<'a> {
            supplier: &'a str,
            mpn: &'a str,
            include_raw: bool,
            max_results: u32,
        }
        let query = Query {
            supplier,
            mpn,
            include_raw: options.include_raw,
            max_results: options.max_results,
        };
        let request = self
            .authenticated_request("search", Method::GET, "v1/search")?
            .query(&query);
        let envelope: SearchEnvelope = self
            .execute("search", ContractRoot::SearchEnvelope, request)
            .await?;
        let provider_error = envelope.status.to_string() == "provider_error";
        Ok(ProviderOutcome::classify(envelope, provider_error))
    }

    /// Look up supplier detail with default options.
    pub async fn detail(
        &self,
        supplier: &str,
        part: &str,
    ) -> Result<ProviderOutcome<DetailEnvelope>, ClientError> {
        self.detail_with_options(supplier, part, LookupOptions::default())
            .await
    }

    /// Look up supplier detail with explicit raw-data options.
    pub async fn detail_with_options(
        &self,
        supplier: &str,
        part: &str,
        options: LookupOptions,
    ) -> Result<ProviderOutcome<DetailEnvelope>, ClientError> {
        #[derive(Serialize)]
        struct Query<'a> {
            supplier: &'a str,
            part: &'a str,
            include_raw: bool,
        }
        let query = Query {
            supplier,
            part,
            include_raw: options.include_raw,
        };
        let request = self
            .authenticated_request("detail", Method::GET, "v1/detail")?
            .query(&query);
        let envelope: DetailEnvelope = self
            .execute("detail", ContractRoot::DetailEnvelope, request)
            .await?;
        let provider_error = envelope.status.to_string() == "provider_error";
        Ok(ProviderOutcome::classify(envelope, provider_error))
    }

    /// Look up an exact supplier part number with default options.
    pub async fn spn(
        &self,
        supplier: &str,
        spn: &str,
    ) -> Result<ProviderOutcome<SpnEnvelope>, ClientError> {
        self.spn_with_options(supplier, spn, LookupOptions::default())
            .await
    }

    /// Look up an exact supplier part number with explicit raw-data options.
    pub async fn spn_with_options(
        &self,
        supplier: &str,
        spn: &str,
        options: LookupOptions,
    ) -> Result<ProviderOutcome<SpnEnvelope>, ClientError> {
        #[derive(Serialize)]
        struct Query<'a> {
            supplier: &'a str,
            spn: &'a str,
            include_raw: bool,
        }
        let query = Query {
            supplier,
            spn,
            include_raw: options.include_raw,
        };
        let request = self
            .authenticated_request("spn", Method::GET, "v1/spn")?
            .query(&query);
        let envelope: SpnEnvelope = self
            .execute("spn", ContractRoot::SpnEnvelope, request)
            .await?;
        let provider_error = envelope.status.to_string() == "provider_error";
        Ok(ProviderOutcome::classify(envelope, provider_error))
    }

    /// Look up multiple exact supplier part numbers with default options.
    pub async fn spn_batch(
        &self,
        supplier: &str,
        spns: Vec<String>,
    ) -> Result<ProviderOutcome<SpnBatchEnvelope>, ClientError> {
        self.spn_batch_with_options(supplier, spns, LookupOptions::default())
            .await
    }

    /// Look up multiple exact supplier part numbers with explicit options.
    pub async fn spn_batch_with_options(
        &self,
        supplier: &str,
        spns: Vec<String>,
        options: LookupOptions,
    ) -> Result<ProviderOutcome<SpnBatchEnvelope>, ClientError> {
        let model = SpnBatchRequest {
            include_raw: options.include_raw,
            spns,
            supplier: supplier.to_owned(),
        };
        let payload = encode(
            ContractRoot::SpnBatchRequest,
            &model,
            scm_contracts::DEFAULT_MAX_BYTES,
        )
        .map_err(|error| ClientError::Contract {
            operation: "spn_batch_request",
            failure: ContractFailure::from(&error),
        })?;
        let request = self
            .authenticated_request("spn_batch", Method::POST, "v1/spn/batch")?
            .header(CONTENT_TYPE, "application/json")
            .body(payload);
        let envelope: SpnBatchEnvelope = self
            .execute("spn_batch", ContractRoot::SpnBatchEnvelope, request)
            .await?;
        let provider_error = envelope.status.to_string() == "provider_error";
        Ok(ProviderOutcome::classify(envelope, provider_error))
    }

    /// Search several suppliers with bounded concurrency and per-supplier errors.
    pub async fn search_all<I, S>(&self, mpn: &str, suppliers: I) -> MultiSearchResults
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.search_all_with_options(mpn, suppliers, SearchOptions::default())
            .await
    }

    /// Search several suppliers with bounded concurrency and explicit options.
    pub async fn search_all_with_options<I, S>(
        &self,
        mpn: &str,
        suppliers: I,
        options: SearchOptions,
    ) -> MultiSearchResults
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let mpn: Arc<str> = Arc::from(mpn);
        let tasks = stream::iter(suppliers.into_iter().map(Into::into)).map(|supplier| {
            let client = self.clone();
            let mpn = Arc::clone(&mpn);
            async move {
                let result = client.search_with_options(&supplier, &mpn, options).await;
                (supplier, result)
            }
        });
        tasks
            .buffer_unordered(self.max_concurrency)
            .collect::<BTreeMap<_, _>>()
            .await
    }

    pub(crate) fn public_request(
        &self,
        operation: &'static str,
        method: Method,
        path: &str,
    ) -> Result<RequestBuilder, ClientError> {
        let endpoint = self
            .base_url
            .join(path)
            .map_err(|_| ClientError::Endpoint { operation })?;
        Ok(self.transport.request(method, endpoint))
    }

    fn authenticated_request(
        &self,
        operation: &'static str,
        method: Method,
        path: &str,
    ) -> Result<RequestBuilder, ClientError> {
        let token = self
            .bearer_token
            .as_ref()
            .ok_or(ClientError::MissingBearerToken)?;
        Ok(self
            .public_request(operation, method, path)?
            .header(AUTHORIZATION, token.clone()))
    }

    async fn execute<T: DeserializeOwned>(
        &self,
        operation: &'static str,
        root: ContractRoot,
        request: RequestBuilder,
    ) -> Result<T, ClientError> {
        let response = request
            .send()
            .await
            .map_err(|source| ClientError::Transport { operation, source })?;
        let status = response.status();
        let payload = read_bounded(response, operation, self.max_response_bytes).await?;
        if !status.is_success() {
            return Err(ClientError::Http {
                operation,
                status: status.as_u16(),
            });
        }
        decode(root, &payload, self.max_response_bytes).map_err(|error| ClientError::Contract {
            operation,
            failure: ContractFailure::from(&error),
        })
    }
}

impl fmt::Debug for ScmClient {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ScmClient")
            .field("base_url", &self.base_url)
            .field("has_bearer_token", &self.bearer_token.is_some())
            .field("max_response_bytes", &self.max_response_bytes)
            .field("max_concurrency", &self.max_concurrency)
            .finish_non_exhaustive()
    }
}

async fn read_bounded(
    mut response: Response,
    operation: &'static str,
    limit: usize,
) -> Result<Vec<u8>, ClientError> {
    if response
        .content_length()
        .is_some_and(|length| length > limit as u64)
    {
        return Err(ClientError::ResponseTooLarge { operation, limit });
    }
    let mut output = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|source| ClientError::Transport { operation, source })?
    {
        if output
            .len()
            .checked_add(chunk.len())
            .is_none_or(|size| size > limit)
        {
            return Err(ClientError::ResponseTooLarge { operation, limit });
        }
        output.extend_from_slice(&chunk);
    }
    Ok(output)
}
