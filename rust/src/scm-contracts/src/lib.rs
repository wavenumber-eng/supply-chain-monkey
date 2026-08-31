#![forbid(unsafe_code)]

//! Generated structural contracts and strict codecs for Supply Chain Monkey.

mod codec;
#[rustfmt::skip]
mod generated;

pub use codec::{CodecError, DEFAULT_MAX_BYTES, decode, encode};
pub use generated::*;
