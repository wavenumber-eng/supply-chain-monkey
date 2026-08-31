//! Secure client construction and transport policy.

use std::fmt;
use std::time::Duration;

use reqwest::header::HeaderValue;
use reqwest::{Certificate, Proxy, Url, redirect};

use crate::{ConfigError, ScmClient};

/// Default whole-request timeout.
pub const DEFAULT_REQUEST_TIMEOUT: Duration = Duration::from_secs(30);
/// Default connection-establishment timeout.
pub const DEFAULT_CONNECT_TIMEOUT: Duration = Duration::from_secs(10);

/// Builder for a bounded, redirect-free SCM HTTP client.
pub struct ClientBuilder {
    base_url: Url,
    bearer_token: Option<HeaderValue>,
    request_timeout: Duration,
    connect_timeout: Duration,
    max_response_bytes: usize,
    max_concurrency: usize,
    root_certificates: Vec<Certificate>,
    proxy: Option<Proxy>,
}

impl ClientBuilder {
    pub(crate) fn new(base_url: &str) -> Result<Self, ConfigError> {
        let base_url = parse_service_url(base_url)?;
        Ok(Self {
            base_url,
            bearer_token: None,
            request_timeout: DEFAULT_REQUEST_TIMEOUT,
            connect_timeout: DEFAULT_CONNECT_TIMEOUT,
            max_response_bytes: scm_contracts::DEFAULT_MAX_BYTES,
            max_concurrency: 4,
            root_certificates: Vec::new(),
            proxy: None,
        })
    }

    /// Configure a bearer token held only in a sensitive authorization header.
    pub fn bearer_token(mut self, token: &str) -> Result<Self, ConfigError> {
        if token.is_empty() {
            return Err(ConfigError::InvalidBearerToken);
        }
        let mut value = HeaderValue::from_str(&format!("Bearer {token}"))
            .map_err(|_| ConfigError::InvalidBearerToken)?;
        value.set_sensitive(true);
        self.bearer_token = Some(value);
        Ok(self)
    }

    /// Set the maximum duration of an entire request, including its body.
    pub const fn request_timeout(mut self, timeout: Duration) -> Self {
        self.request_timeout = timeout;
        self
    }

    /// Set the maximum connection-establishment duration.
    pub const fn connect_timeout(mut self, timeout: Duration) -> Self {
        self.connect_timeout = timeout;
        self
    }

    /// Set the maximum accepted response body size.
    pub const fn max_response_bytes(mut self, max_bytes: usize) -> Self {
        self.max_response_bytes = max_bytes;
        self
    }

    /// Set the maximum number of simultaneous multi-provider searches.
    pub const fn max_concurrency(mut self, max_concurrency: usize) -> Self {
        self.max_concurrency = max_concurrency;
        self
    }

    /// Merge private PEM root certificates with the platform trust roots.
    pub fn add_root_certificates_pem(mut self, pem: &[u8]) -> Result<Self, ConfigError> {
        let certificates =
            Certificate::from_pem_bundle(pem).map_err(|_| ConfigError::InvalidRootCertificate)?;
        if certificates.is_empty() {
            return Err(ConfigError::InvalidRootCertificate);
        }
        self.root_certificates.extend(certificates);
        Ok(self)
    }

    /// Route requests through an explicit HTTP or HTTPS proxy.
    pub fn proxy(mut self, proxy_url: &str) -> Result<Self, ConfigError> {
        validate_proxy_url(proxy_url)?;
        self.proxy = Some(Proxy::all(proxy_url).map_err(|_| ConfigError::InvalidProxy)?);
        Ok(self)
    }

    /// Construct the reusable async client.
    pub fn build(mut self) -> Result<ScmClient, ConfigError> {
        validate_bounds(&self)?;
        validate_authenticated_scheme(&self)?;
        normalize_base_path(&mut self.base_url);
        let mut transport = reqwest::Client::builder()
            .redirect(redirect::Policy::none())
            .timeout(self.request_timeout)
            .connect_timeout(self.connect_timeout)
            .user_agent(concat!("scm-client/", env!("CARGO_PKG_VERSION")));
        if !self.root_certificates.is_empty() {
            transport = transport.tls_certs_merge(self.root_certificates);
        }
        if let Some(proxy) = self.proxy {
            transport = transport.proxy(proxy);
        }
        let transport = transport.build().map_err(ConfigError::HttpClientBuild)?;
        Ok(ScmClient::from_parts(
            transport,
            self.base_url,
            self.bearer_token,
            self.max_response_bytes,
            self.max_concurrency,
        ))
    }
}

impl fmt::Debug for ClientBuilder {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ClientBuilder")
            .field("base_url", &self.base_url)
            .field("has_bearer_token", &self.bearer_token.is_some())
            .field("request_timeout", &self.request_timeout)
            .field("connect_timeout", &self.connect_timeout)
            .field("max_response_bytes", &self.max_response_bytes)
            .field("max_concurrency", &self.max_concurrency)
            .field("private_root_count", &self.root_certificates.len())
            .field("has_explicit_proxy", &self.proxy.is_some())
            .finish()
    }
}

fn parse_service_url(source: &str) -> Result<Url, ConfigError> {
    let url = Url::parse(source).map_err(|_| ConfigError::InvalidBaseUrl)?;
    if !matches!(url.scheme(), "http" | "https") || url.host().is_none() {
        return Err(ConfigError::UnsupportedScheme);
    }
    if !url.username().is_empty() || url.password().is_some() {
        return Err(ConfigError::BaseUrlCredentials);
    }
    if url.query().is_some() || url.fragment().is_some() {
        return Err(ConfigError::BaseUrlQueryOrFragment);
    }
    Ok(url)
}

fn validate_proxy_url(source: &str) -> Result<(), ConfigError> {
    let url = Url::parse(source).map_err(|_| ConfigError::InvalidProxy)?;
    let valid = matches!(url.scheme(), "http" | "https")
        && url.host().is_some()
        && url.username().is_empty()
        && url.password().is_none()
        && url.query().is_none()
        && url.fragment().is_none();
    if !valid {
        return Err(ConfigError::InvalidProxy);
    }
    Ok(())
}

fn validate_bounds(builder: &ClientBuilder) -> Result<(), ConfigError> {
    for (name, zero) in [
        ("request timeout", builder.request_timeout.is_zero()),
        ("connect timeout", builder.connect_timeout.is_zero()),
        ("response limit", builder.max_response_bytes == 0),
        ("concurrency limit", builder.max_concurrency == 0),
    ] {
        if zero {
            return Err(ConfigError::ZeroBound(name));
        }
    }
    Ok(())
}

fn validate_authenticated_scheme(builder: &ClientBuilder) -> Result<(), ConfigError> {
    if builder.bearer_token.is_some()
        && builder.base_url.scheme() != "https"
        && !is_loopback(&builder.base_url)
    {
        return Err(ConfigError::AuthenticatedRemoteHttp);
    }
    Ok(())
}

fn is_loopback(url: &Url) -> bool {
    let Some(host) = url.host_str() else {
        return false;
    };
    host.eq_ignore_ascii_case("localhost")
        || host
            .parse::<std::net::IpAddr>()
            .is_ok_and(|address| address.is_loopback())
}

fn normalize_base_path(url: &mut Url) {
    if !url.path().ends_with('/') {
        let mut path = url.path().to_owned();
        path.push('/');
        url.set_path(&path);
    }
}
