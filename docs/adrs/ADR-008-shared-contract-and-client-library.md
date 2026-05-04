# ADR-008: Shared Contract and Client Library

## Status

Proposed

## Context

lib_cruncher and bom_cruncher need to consume the supply-chain-monkey API. Both
currently import provider adapters directly from `toolz/supply_chain_monkey`. The
transition plan calls for switching to HTTP.

The question is how to structure the client code and shared types so that:

- Server and client agree on response shapes (the contract)
- Consumers don't need to install the full server to use the client
- API changes are caught by tests in one place
- The repo stays simple (one pyproject.toml, no workspace)

Options considered:

1. **Three separate packages** (scm_contract, scm_client, supply_chain_monkey) in a
   uv workspace. Adds three pyproject.toml files and workspace config.

2. **Separate repo** for the client. Versioning drift between client and server.

3. **One package with optional dependencies.** Contract and client at the top level,
   server behind an optional extra. Single pyproject.toml.

## Decision

Option 3: one package (`scm`) with optional dependencies.

### Package layout

```
src/py/
  scm/
    __init__.py
    models.py          # PartResponse, ServiceEnvelope, SupplierType, enums
    client.py          # SCMClient — thin HTTP wrapper
    server/            # FastAPI app, providers, routers, templates
      __init__.py
      main.py
      settings.py
      auth.py
      routers/
      providers/
      templates/
```

### Dependencies

```toml
[project]
name = "scm"
dependencies = ["pydantic>=2.0"]

[project.optional-dependencies]
client = ["requests>=2.32.0"]
server = ["fastapi>=0.115.0", "uvicorn[standard]>=0.34.0", "requests>=2.32.0"]
```

- `scm` alone: just the models (the contract)
- `scm[client]`: models + HTTP client
- `scm[server]`: models + client + full server with providers

### Consumer usage

```toml
# lib_cruncher / bom_cruncher
[tool.uv.sources]
scm = { git = "https://github.com/<org>/supply-chain-monkey.git" }

[project]
dependencies = ["scm[client]"]
```

```python
from scm.models import PartResponse, ServiceEnvelope
from scm.client import SCMClient

client = SCMClient(url="https://your-scm.example.com", token="...")
results = client.search_all("TPS543620RPYR")
```

### Contract = the models

`scm.models` is the contract between server and client:

- `SupplierType` enum
- `PartResponse` — part data shape
- `ServiceEnvelope` — response wrapper with status, timing, metadata
- `PARAMETER_FIELD_NAMES` — maps supplier to field name for downstream consumers

Both `scm.client` and `scm.server` import from `scm.models`. If the server
changes a response shape, the model changes, and the client tests (which run
against the server via FastAPI's TestClient) catch it immediately.

### Client API

```python
class SCMClient:
    def __init__(self, url: str, token: str): ...

    def search(self, supplier: str, mpn: str) -> ServiceEnvelope:
        """Search a single supplier."""

    def search_all(self, mpn: str) -> dict[str, ServiceEnvelope]:
        """Search all suppliers in parallel. Returns {supplier_name: envelope}."""

    def detail(self, supplier: str, part: str) -> ServiceEnvelope:
        """Get detail for a single part."""

    def health(self) -> dict:
        """Check service health."""

    def providers_status(self) -> dict:
        """Get provider configuration status."""
```

`search_all` uses `concurrent.futures.ThreadPoolExecutor` to fire requests in
parallel, same pattern as the web UI test panel.

### Appliku deploy command

The server import path changes from `supply_chain_monkey.main:app` to
`scm.server.main:app`:

```yaml
services:
  web:
    command: bash -c 'PYTHONPATH=/code/src/py uvicorn scm.server.main:app --host 0.0.0.0 --port 8000'
```

### Migration

This requires renaming the Python package from `supply_chain_monkey` to `scm`.
Internal imports change but the API contract stays the same. The rename is
contained within this repo — consumers switch from `import supply_chain_monkey`
to `from scm.client import SCMClient`.

## Consequences

- Single pyproject.toml, no workspace complexity
- Consumers install only what they need via extras
- Contract (models) shared by server and client, tested together
- Package rename from `supply_chain_monkey` to `scm`
- Appliku command path changes
- Existing tests need import path updates
