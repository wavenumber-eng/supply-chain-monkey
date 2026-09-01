//! Client configuration, transport, HTTP, and contract errors.

use scm_contracts::CodecError;
use thiserror::Error;

/// Invalid client configuration.
#[derive(Debug, Error)]
pub enum ConfigError {
    /// The base URL could not be parsed.
    #[error("invalid SCM base URL")]
    InvalidBaseUrl,
    /// Only HTTP and HTTPS service URLs are meaningful.
    #[error("SCM base URL must use http or https")]
    UnsupportedScheme,
    /// Credentials must be carried only in the authorization header.
    #[error("SCM base URL must not contain credentials")]
    BaseUrlCredentials,
    /// Query strings and fragments do not belong in a service base URL.
    #[error("SCM base URL must not contain a query or fragment")]
    BaseUrlQueryOrFragment,
    /// Authenticated non-loopback services must use TLS.
    #[error("authenticated remote SCM endpoints require https")]
    AuthenticatedRemoteHttp,
    /// A proxy must never receive loopback-development bearer traffic.
    #[error("authenticated loopback HTTP cannot use an explicit proxy")]
    AuthenticatedLoopbackProxy,
    /// The bearer token was empty or could not be represented as a header.
    #[error("invalid SCM bearer token")]
    InvalidBearerToken,
    /// A private root certificate was malformed.
    #[error("invalid PEM root certificate bundle")]
    InvalidRootCertificate,
    /// The explicit proxy URL was malformed or unsafe.
    #[error("invalid SCM proxy URL")]
    InvalidProxy,
    /// A configured bound was zero.
    #[error("{0} must be greater than zero")]
    ZeroBound(&'static str),
    /// Reqwest could not build the configured transport.
    #[error("could not build SCM HTTP transport")]
    HttpClientBuild(#[source] reqwest::Error),
}

/// Sanitized phase in which contract enforcement failed.
#[derive(Clone, Copy, Debug, Eq, Error, PartialEq)]
pub enum ContractFailure {
    /// The encoded request or response exceeded its contract bound.
    #[error("payload bound")]
    PayloadTooLarge,
    /// Strict JSON or I-JSON preflight failed.
    #[error("strict JSON preflight")]
    Json,
    /// JSON Schema validation failed.
    #[error("schema validation")]
    Schema,
    /// Generated native model conversion failed.
    #[error("generated model conversion")]
    Model,
}

impl From<&CodecError> for ContractFailure {
    fn from(error: &CodecError) -> Self {
        match error {
            CodecError::PayloadTooLarge { .. } => Self::PayloadTooLarge,
            CodecError::Json(_) => Self::Json,
            CodecError::Schema(_) => Self::Schema,
            CodecError::Model(_) => Self::Model,
        }
    }
}

/// Failure while executing an SCM request.
#[derive(Debug, Error)]
pub enum ClientError {
    /// An authenticated operation was attempted without credentials.
    #[error("SCM bearer token is not configured")]
    MissingBearerToken,
    /// A static endpoint could not be joined to the configured base URL.
    #[error("could not construct SCM endpoint for {operation}")]
    Endpoint {
        /// Stable operation name used without request data or credentials.
        operation: &'static str,
    },
    /// The HTTP exchange failed before a response was available.
    #[error("SCM transport failed during {operation}")]
    Transport {
        /// Stable operation name used without request data or credentials.
        operation: &'static str,
        /// Underlying sanitized HTTP transport error.
        #[source]
        source: reqwest::Error,
    },
    /// The response exceeded the configured body limit.
    #[error("SCM response during {operation} exceeded {limit} bytes")]
    ResponseTooLarge {
        /// Stable operation name used without request data or credentials.
        operation: &'static str,
        /// Configured maximum response size in bytes.
        limit: usize,
    },
    /// The server returned a non-success HTTP status.
    #[error("SCM HTTP status {status} during {operation}")]
    Http {
        /// Stable operation name used without request data or credentials.
        operation: &'static str,
        /// HTTP response status code.
        status: u16,
    },
    /// A request or response failed the generated wire contract.
    #[error("SCM contract failure during {operation}")]
    Contract {
        /// Stable operation name used without request data or credentials.
        operation: &'static str,
        /// Contract-enforcement phase that rejected the payload.
        failure: ContractFailure,
    },
}
