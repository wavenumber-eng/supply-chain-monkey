# supply-chain-monkey-contracts

Generated Supply Chain Monkey v1 wire models and a strict, bounded JSON codec.

The checked-in Rust types and package-local JSON Schema resources are generated
from the repository's TypeSpec authority. Consumers should use the public model
types together with `decode` and `encode`; schema resources are implementation
details used to enforce the wire contract at runtime.
