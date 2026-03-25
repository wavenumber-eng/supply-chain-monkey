# ADR-002: Source Layout Reorganization

## Status

Proposed

## Context

The codebase was copied from `toolz/supply_chain_monkey` which had a flat layout — all
provider files, the interface, scrapers, and helpers at the same level under
`src/py/supply_chain_monkey/`. This worked fine as a library package.

As a FastAPI service, we now have two distinct concerns:

1. HTTP layer (routes, auth, request/response models)
2. Provider layer (vendor adapters, scrapers, API clients)

Keeping everything flat will make it harder to reason about what's HTTP-facing vs
internal business logic as the service grows.

## Decision

Reorganize into two subdirectories under `src/py/supply_chain_monkey/`:

```
src/py/supply_chain_monkey/
  main.py              # FastAPI app entry point
  settings.py          # env var loading, config
  auth.py              # bearer token dependency
  models.py            # shared Pydantic models, response envelope
  routers/
    __init__.py
    health.py          # GET /v1/health, GET /v1/providers/status
    search.py          # GET /v1/search
    detail.py          # GET /v1/detail
  providers/
    __init__.py
    base.py            # SupplierInterface ABC, SupplierType, SupplierPartInfo, factory
    jlc.py             # JLCPCBSupplier
    jlc_scraper.py     # scraper functions
    jlc_openapi.py     # official API client
    lcsc.py            # LCSCSupplier
    lcsc_scraper.py    # scraper functions
    digikey.py         # DigikeySupplier
    mouser.py          # MouserSupplier
    claude_helper.py   # Claude AI scraper fallback
```

### What moves where

| Current file | New location |
|---|---|
| `supplier_interface.py` | `providers/base.py` |
| `jlcpcb_supplier.py` | `providers/jlc.py` |
| `jlc_scraper.py` | `providers/jlc_scraper.py` |
| `jlc_openapi.py` | `providers/jlc_openapi.py` |
| `lcsc_supplier.py` | `providers/lcsc.py` |
| `lcsc_scraper.py` | `providers/lcsc_scraper.py` |
| `digikey_supplier.py` | `providers/digikey.py` |
| `mouser_supplier.py` | `providers/mouser.py` |
| `claude_scraper_helper.py` | `providers/claude_helper.py` |
| `env.py` | removed; replaced by `settings.py` |

### New files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app creation, router registration, startup |
| `settings.py` | Load all config from env vars, single source of truth |
| `auth.py` | Bearer token verification as a FastAPI dependency |
| `models.py` | Pydantic response models, response envelope |
| `routers/health.py` | Health and provider status endpoints |
| `routers/search.py` | Search endpoint |
| `routers/detail.py` | Detail endpoint |

## Consequences

- Clear separation between HTTP concerns and provider logic
- Providers can be tested independently of FastAPI
- Routers stay thin — they validate input, call providers, wrap responses
- Import paths change (e.g., `from .providers.base import SupplierInterface`)
- Existing tests will need import path updates
