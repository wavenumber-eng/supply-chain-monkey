# supply-chain-monkey-client

Async, typed client for the Supply Chain Monkey v1 API.

The client uses the generated `scm-contracts` models and strict codec, rustls
with the platform certificate verifier, disabled redirects, bounded response
bodies, and sensitive bearer headers. Authenticated remote endpoints require
HTTPS; plain HTTP is accepted only for explicit loopback development servers.

The deprecated query-token event stream is intentionally not supported.

Generated response types are available through `scm_client::contracts`, so a
client consumer does not need a second direct dependency merely to name them.
