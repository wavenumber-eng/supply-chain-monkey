# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Directives

- No emojis in code, docs, or commit messages
- No marketing language ("production ready", "enterprise-grade", "battle-tested", etc.)
- Be factual and direct about what works and what doesn't
- Short, simple commit messages. No fluff.
- Place temporary/intermediate files in `/temp` (gitignored)
- All decisions about structure, organization, or API changes must have an ADR in `docs/adrs/` before implementation

## Project

supply-chain-monkey is a standalone FastAPI service for querying electronic component suppliers. It centralizes vendor credentials, caching, and provider routing behind an internal HTTP API.

Migrated from `toolz/supply_chain_monkey`. The provider adapter logic originates there.

## Stack

- Python 3.13, FastAPI, uvicorn
- Deployed via Appliku on DigitalOcean
- No database in v1 (in-memory cache, env var config)
- uv for dependency management

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
    cache.py
    models.py
    routers/
    providers/
  tests/
  docs/
    plans/
    adrs/
    requirements/
```

## Deployment

- Appliku push-to-deploy from GitHub
- Build image: python-3.13-uv
- App binds to 0.0.0.0:8000
- All credentials and tokens set as env vars in Appliku dashboard
- No Procfile or custom Dockerfile needed; processes defined in appliku.yml

## Testing

```bash
uv run pytest
```
