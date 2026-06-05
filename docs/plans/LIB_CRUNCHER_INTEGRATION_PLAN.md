# Completed Plan: Lib Cruncher SCM Integration

## Status

Completed. `lib_cruncher` imports `scm.client.SCMClient` and depends on the
sibling `supply-chain-monkey` source package during local development.

## Current Contract

`lib_cruncher` should depend on the PyPI distribution spelling:

```toml
dependencies = ["supply-chain-monkey[client]"]
```

Local development can override that dependency with a sibling source checkout:

```toml
[tool.uv.sources]
supply-chain-monkey = { path = "../../supply-chain-monkey", editable = true }
```

Runtime code imports the client package:

```python
from scm.client import SCMClient
from scm.models import ServiceEnvelope, SupplierType
```

## Boundaries

- Supplier credentials belong to the deployed Supply Chain Monkey service.
- `lib_cruncher` owns its UI and local response adaptation.
- `lib_cruncher` must not import `scm.server.providers` or supplier adapters.
- If local supplier access is needed, run the SCM server locally and point
  `SCM_URL` at it.

## Remaining Test Gap

`lib_cruncher` still needs focused fast-lane tests for its SCM-backed search,
single-supplier search, and SSE stream routes using a fake `SCMClient` or mocked
HTTP responses.
