#![forbid(unsafe_code)]

//! Async Supply Chain Monkey client library.

mod client;
mod config;
mod error;

pub use client::{
    DEFAULT_SUPPLIERS, LookupOptions, MultiSearchResults, ProviderOutcome, ScmClient, SearchOptions,
};
pub use config::{ClientBuilder, DEFAULT_CONNECT_TIMEOUT, DEFAULT_REQUEST_TIMEOUT};
pub use error::{ClientError, ConfigError, ContractFailure};
