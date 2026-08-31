# Supply Chain Monkey Design

Maintained design records live in:

- `docs/adrs/`
- `docs/requirements/REQUIREMENTS.md`
- `docs/guides/APPLIKU_FASTAPI_DEPLOYMENT.md`
- `docs/scm/design/v1-contract-inventory.md`

The PyPI distribution name is `supply-chain-monkey`; the Python import package
is `scm`. No alternate import package is supported.

The repo intentionally keeps client and server code together:

- `scm.models` and `scm.client` are the consumer-facing library surface.
- `scm.server` is the deployed Appliku service surface.
