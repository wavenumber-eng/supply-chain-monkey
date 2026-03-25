# supply-chain-monkey

Internal service for querying electronic component suppliers (JLCPCB, LCSC, Digikey, Mouser). Provides a unified HTTP API that centralizes vendor credentials, caching, and rate limiting.

## Status

Early development. Not yet deployed.

## What This Does

- Accepts search and detail requests for electronic components
- Routes to the appropriate vendor API or scraper
- Returns normalized part data (stock, pricing, datasheets, parameters)
- Keeps vendor credentials server-side only

## Stack

- Python 3.13, FastAPI
- Deployed via Appliku (Docker, push-to-deploy)

## Development

```bash
uv sync
uv run uvicorn supply_chain_monkey.main:app --reload
```

## Deployment

Push to the deployment branch. Appliku handles build and deploy from `appliku.yml`.
