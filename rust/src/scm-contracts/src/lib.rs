#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! TypeSpec-generated SCM v1 structural contracts and strict JSON codec.
//!
//! Handwritten code owns the bounded [`decode`] and [`encode`] entry points.
//! Model modules are deterministic projections of the checked-in SCM TypeSpec
//! JSON Schemas and must not be edited directly.
//!
//! ```
//! use scm_contracts::{ContractRoot, HealthResponse, decode};
//!
//! let response: HealthResponse = decode(
//!     ContractRoot::HealthResponse,
//!     br#"{"status":"ok"}"#,
//!     1024,
//! )?;
//! assert_eq!(response.status.to_string(), "ok");
//! # Ok::<(), scm_contracts::CodecError>(())
//! ```

mod codec;
#[rustfmt::skip]
#[allow(
    missing_docs,
    reason = "generated projections inherit semantic documentation from TypeSpec schemas"
)]
mod generated;

pub use codec::{CodecError, DEFAULT_MAX_BYTES, decode, encode};
pub use generated::*;
