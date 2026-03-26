# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Directives

- No emojis in code, docs, or commit messages
- No marketing language ("production ready", "enterprise-grade", "battle-tested", etc.)
- Be factual and direct about what works and what doesn't
- Short, simple commit messages. No fluff. No "Co-Authored-By" lines.
- Place temporary/intermediate files in `/temp` (gitignored)
- All decisions about structure, organization, or API changes must have an ADR in `docs/adrs/` before implementation

## Project

supply-chain-monkey is a standalone FastAPI service for querying electronic component suppliers (JLCPCB, LCSC, Digikey, Mouser). Centralizes vendor credentials and provider routing behind an internal HTTP API.

Deployed at https://scm.wavenumber.net. Migrated from `toolz/supply_chain_monkey`.

## Stack

- Python 3.13, FastAPI, uvicorn
- Deployed via Appliku on DigitalOcean (python-3.13-uv build image)
- Stateless — no database, env var config
- uv for dependency management
- `pyproject.toml` uses `tool.uv.package = false` (not an installable package)
- PYTHONPATH used to locate source at runtime

## Repo Layout

```
supply-chain-monkey/
  appliku.yml
  pyproject.toml
  uv.lock
  src/py/supply_chain_monkey/
    main.py
    settings.py
    auth.py
    models.py
    templates/
    routers/
      common.py
      health.py
      search.py
      detail.py
    providers/
      base.py
      jlc.py, jlc_scraper.py, jlc_openapi.py
      lcsc.py, lcsc_api.py
      digikey.py
      mouser.py
  tests/
  docs/
    plans/
    adrs/
    requirements/
    guides/
```

## Deployment

- Push to `production` branch triggers Appliku deploy
- Build image: python-3.13-uv
- App binds to 0.0.0.0:8000
- All credentials and tokens set as env vars in Appliku dashboard

## Testing

```bash
uv run pytest
```
