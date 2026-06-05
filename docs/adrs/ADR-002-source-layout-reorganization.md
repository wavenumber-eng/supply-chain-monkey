# ADR-002: Source Layout Reorganization

## Status

Accepted.

## Context

Supply Chain Monkey started from a flatter supplier-library layout. As it became
both a deployed FastAPI service and a reusable client package, the repo needed a
clear separation between public contracts, consumer HTTP access, server routes,
and supplier provider adapters.

## Decision

Use one import package, `scm`, under `src/py/`:

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
      health.py
      search.py
      detail.py
      stream.py
    providers/
      base.py
      jlc.py
      jlc_scraper.py
      jlc_openapi.py
      lcsc.py
      lcsc_api.py
      lcsc_scraper.py
      digikey.py
      mouser.py
      claude_helper.py
```

`scm.models` and `scm.client` are the consumer-facing package surface.
`scm.server` is the deployed service surface.

## Consequences

- HTTP concerns and provider logic are separate.
- Consumer applications can install `supply-chain-monkey[client]` and import
  `scm.client` without reaching into provider modules.
- Provider adapters can be tested independently of FastAPI route behavior.
- Alternate import-path compatibility is intentionally not preserved.
