# ADR-001: Supplier Interface Architecture

## Status

Accepted.

## Context

Supply Chain Monkey integrates multiple electronic component suppliers with
different API shapes, authentication rules, rate limits, and fallback behavior.
The service needs a common provider interface so supplier-specific details stay
inside `scm.server.providers` while the HTTP and client contracts stay stable.

The current PyPI distribution is `supply-chain-monkey`. The Python import
package is `scm`.

## Decision

All supplier adapters implement the same provider contract:

- identify themselves with `SupplierType`
- expose a stable downstream parameter field name
- search by manufacturer part number
- fetch detail by supplier part number
- return normalized `SupplierPartInfo` values
- degrade gracefully when credentials, networks, or provider APIs fail

Provider construction goes through `create_supplier()` in
`scm.server.providers.base`. Consumer applications must call the HTTP service
through `scm.client.SCMClient`; they must not import provider adapters directly.

## Current Layout

```text
supply-chain-monkey/
  src/py/scm/
    models.py
    client.py
    server/
      main.py
      settings.py
      auth.py
      routers/
      providers/
  tests/
  docs/
```

## Credential Policy

Provider credentials are read through `scm.server.settings` from process
environment/configuration owned by the deployment host. Provider modules must
not load local `.env` files or mutate environment state at import time.

## Consequences

- Server code owns supplier-specific credentials and integration behavior.
- Client code consumes only shared contracts and HTTP responses.
- Adding a supplier requires provider tests and API-envelope coverage.
- Missing credentials or provider failures should return graceful provider
  status/error responses instead of crashing unrelated suppliers.
