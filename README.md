# supply-chain-monkey

Internal service for querying electronic component suppliers. Provides a unified HTTP API that centralizes vendor credentials and provider routing.

## Status

v1.0.0 — deployed at https://scm.wavenumber.net

## Providers

| Supplier | Backend | Credentials Required |
|----------|---------|---------------------|
| JLCPCB | Hybrid (official API + scraper) | Optional (scraper works without) |
| LCSC | Internal JSON API | None |
| Digikey | Official REST API v4 (OAuth2) | Yes |
| Mouser | Official REST API v1 | Yes |

## API

All endpoints except health require a bearer token in the `Authorization` header.

```
GET  /v1/health                              # no auth
GET  /v1/providers/status                    # provider config status
GET  /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR
GET  /v1/detail?supplier=jlcpcb&part=C2870085
```

Responses are wrapped in an envelope:

```json
{
    "status": "ok",
    "supplier": "JLCPCB",
    "parameter_field_name": "JLCPCB Part #",
    "provider_latency_ms": 1035,
    "service_timestamp": "2026-03-26T...",
    "cached": false,
    "data": [...]
}
```

The root URL serves a status page with an interactive test panel.

## Stack

- Python 3.13, FastAPI, uvicorn
- Deployed via Appliku on DigitalOcean (push-to-deploy)
- No database (stateless, env var config)
- uv for dependency management

## Development

```bash
cp .env.template .env
# fill in SCM_SERVICE_TOKEN and any provider credentials

uv sync
PYTHONPATH=src/py uv run uvicorn supply_chain_monkey.main:app --reload --env-file .env
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

Push to the `production` branch. Appliku builds and deploys automatically.

```bash
git checkout production && git merge main && git push && git checkout main
```
