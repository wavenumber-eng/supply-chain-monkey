# ADR-008: Shared Contract and Client Library

## Status

Accepted.

## Decision

Supply Chain Monkey is one PyPI distribution with one import package:

- PyPI distribution: `supply-chain-monkey`
- Python import package: `scm`

The repo keeps client and server code together so contracts are versioned and
tested together.

## Package Layout

```text
src/py/scm/
  __init__.py
  models.py
  client.py
  server/
    __init__.py
    main.py
    settings.py
    auth.py
    routers/
    providers/
    templates/
```

## Consumer Contract

Consumers depend on:

```toml
dependencies = ["supply-chain-monkey[client]"]
```

Consumers import:

```python
from scm.client import SCMClient
from scm.models import ServiceEnvelope, SupplierType
```

`scm.models` is the shared contract between client and server. `scm.client`
serializes/deserializes those contracts over HTTP. `scm.server` owns provider
adapters and credentials.

## Deployment Contract

The Appliku service imports:

```text
scm.server.main:app
```

through the configured command in `appliku.yml`.

## Consequences

- Client and server contract changes are tested in one repository.
- Consumer applications do not import provider adapters directly.
- The public dependency spelling and import spelling are intentionally
  different.
