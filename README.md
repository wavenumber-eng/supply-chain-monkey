# supply-chain-monkey

Internal service for querying electronic component suppliers. It provides a
unified HTTP API that centralizes vendor credentials and provider routing.

## Status

v1.0.1 - standalone service, Python client, and Appliku deployment signoff.

## Architecture

The repo contains three layers:

- `scm.models`: shared contract with Pydantic models, enums, and supplier
  constants.
- `scm.client`: HTTP client library for consumers.
- `scm.server`: FastAPI server with provider adapters and the status page.

## Providers

| Supplier | Backend | Credentials Required |
|---|---|---|
| JLCPCB | Hybrid official API plus scraper | Optional; scraper works without credentials |
| LCSC | Internal JSON API | None |
| Digikey | Official REST API v4 OAuth2 | Yes |
| Mouser | Official REST API v1 | Yes |

## API

All endpoints except health require a bearer token.

```text
GET  /v1/health
GET  /v1/providers/status
GET  /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR
GET  /v1/detail?supplier=jlcpcb&part=C2870085
GET  /v1/search/stream?mpn=X&token=Y
```

The streaming endpoint pushes results per provider as they complete via
Server-Sent Events. It supports `max_results` and per-provider `timeout`.

The root URL serves a status page with an interactive test panel.

## Client Library

```python
from scm.client import SCMClient
from scm.models import PARAMETER_FIELD_NAMES, SUPPLIERS, SupplierType

client = SCMClient(url="https://your-scm.example.com", token="...")

result = client.search("jlcpcb", "TPS543620RPYR")
all_results = client.search_all("TPS543620RPYR")
detail = client.detail("jlcpcb", "C2870085")
print(SUPPLIERS)
```

## Local Development

```bash
cp .env.template .env
# fill in SCM_SERVICE_TOKEN and any provider credentials

uv sync --group dev
PYTHONPATH=src/py uv run uvicorn scm.server.main:app --reload --env-file .env
```

## Testing

```bash
uv run pytest -q
uv run rack run L99_signoff
uv run python tests/scripts/scm_test_cli.py --token YOUR_TOKEN
uv run python tests/scripts/scm_test_cli.py --url https://your-scm.example.com --token YOUR_TOKEN
```

## Deployment

The included `appliku.yml` uses Appliku's managed `python-3.13-uv` build image.
Pushing `production` can trigger deployment.

```bash
git checkout production && git merge main && git push && git checkout main
```

`pyproject.toml` must keep `[tool.uv] package = false` and
`default-groups = []`. The Dockerfile is inactive unless `appliku.yml` changes
to `build_image: dockerfile`. See `CLAUDE.md` for deployment constraints.

## Consumer Integration

Consumers should depend on the `scm` package and configure service URL and token
outside source control. See `docs/plans/LIB_CRUNCHER_INTEGRATION_PLAN.md` for
one integration example.
