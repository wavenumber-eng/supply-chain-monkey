# supply-chain-monkey

Internal service for querying electronic component suppliers. Provides a unified HTTP API that centralizes vendor credentials and provider routing.

## Status

v1.0.0 — deployed at https://scm.wavenumber.net

## Architecture

The repo contains three layers:

- **`scm.models`** — shared contract (Pydantic models, enums, supplier constants). Zero dependencies beyond pydantic.
- **`scm.client`** — HTTP client library for consumers (lib_cruncher, bom_cruncher). Depends on requests.
- **`scm.server`** — FastAPI server with provider adapters. Depends on fastapi, uvicorn, requests.

## Providers

| Supplier | Backend | Credentials Required |
|----------|---------|---------------------|
| JLCPCB | Hybrid (official API + scraper) | Optional (scraper works without) |
| LCSC | Internal JSON API | None |
| Digikey | Official REST API v4 (OAuth2) | Yes |
| Mouser | Official REST API v1 | Yes |

## API

All endpoints except health require a bearer token.

```
GET  /v1/health                              # no auth
GET  /v1/providers/status                    # provider config status
GET  /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR
GET  /v1/detail?supplier=jlcpcb&part=C2870085
GET  /v1/search/stream?mpn=X&token=Y        # SSE streaming, all providers
```

The streaming endpoint pushes results per provider as they complete via Server-Sent Events. Includes `max_results` (default 10) and per-provider `timeout` (default 15s).

The root URL serves a status page with an interactive test panel.

## Client Library

```python
from scm.client import SCMClient
from scm.models import SUPPLIERS, SupplierType, PARAMETER_FIELD_NAMES

client = SCMClient(url="https://scm.wavenumber.net", token="...")

# Search one supplier
result = client.search("jlcpcb", "TPS543620RPYR")

# Search all in parallel
all_results = client.search_all("TPS543620RPYR")

# Detail
detail = client.detail("jlcpcb", "C2870085")

# Enumerate
print(SUPPLIERS)  # ['jlcpcb', 'lcsc', 'digikey', 'mouser']
```

## Local Development

```bash
cp .env.template .env
# fill in SCM_SERVICE_TOKEN and any provider credentials

uv sync
PYTHONPATH=src/py uv run uvicorn scm.server.main:app --reload --env-file .env
```

## Testing

```bash
# Unit tests (no network)
uv run pytest

# Test CLI against local or remote
uv run python tests/scripts/scm_test_cli.py --token YOUR_TOKEN
uv run python tests/scripts/scm_test_cli.py --url https://scm.wavenumber.net --token YOUR_TOKEN
```

## Deployment

Uses Appliku with the managed `python-3.13-uv` build image. Push to `production` triggers deploy.

```bash
git checkout production && git merge main && git push && git checkout main
```

**Important:** `pyproject.toml` must use `[tool.uv] package = false`. See CLAUDE.md for deployment constraints.

## Consumer Integration

Consumers (lib_cruncher, bom_cruncher) add the scm `src/py` directory to `sys.path` at startup and depend on `scm` in their pyproject.toml for dependency resolution. See `docs/plans/LIB_CRUNCHER_INTEGRATION_PLAN.md`.
