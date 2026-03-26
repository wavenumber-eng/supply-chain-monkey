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

supply-chain-monkey is a standalone FastAPI service for querying electronic
component suppliers (JLCPCB, LCSC, Digikey, Mouser). Centralizes vendor
credentials and provider routing behind an internal HTTP API.

Deployed at https://scm.wavenumber.net. Migrated from `toolz/supply_chain_monkey`.

The repo contains three layers:
- `scm.models` — shared contract (Pydantic models, enums, supplier constants)
- `scm.client` — HTTP client library for consumers
- `scm.server` — FastAPI server, provider adapters, routers

## Deployment Rules

**IMPORTANT: Do not change the build/deploy approach without testing a full
Appliku deploy cycle. The constraints below exist because of hard-won lessons.**

### pyproject.toml must use `package = false`

```toml
[tool.uv]
package = false
```

Appliku's managed `python-3.13-uv` build image runs `uv sync --frozen` BEFORE
copying source code. If the project has a `[build-system]`, hatchling tries to
build the package and fails because the source isn't there yet. `package = false`
makes `uv sync` skip the project and only install dependencies.

### appliku.yml must use the managed build image

```yaml
build_settings:
  build_image: python-3.13-uv
  container_port: 8000

services:
  web:
    command: bash -c 'PYTHONPATH=/code/src/py uvicorn scm.server.main:app --host 0.0.0.0 --port 8000'
```

Do NOT use `build_image: dockerfile`. Custom Dockerfiles have context path issues
with Appliku's build system (the `web` and `one_off` targets use different
contexts, `./code/` paths can double, `./env/` is unavailable in the build step).

### The web command must use `bash -c` with PYTHONPATH

Since `package = false`, the `scm` module is not installed in site-packages.
`PYTHONPATH=/code/src/py` makes it importable. The `bash -c '...'` wrapper is
required because Docker exec mode can't handle inline env var assignment.

### Do not add `readme = "README.md"` to pyproject.toml

Hatchling validates it during dependency resolution, before source is copied.

### Consumers import via sys.path, not pip install

Since `package = false`, consumers (like lib_cruncher) add the scm `src/py`
directory to `sys.path` at startup. The appz workspace lists scm as a dependency
for dependency resolution, but the actual import path comes from sys.path.

## Stack

- Python 3.13, FastAPI, uvicorn
- Deployed via Appliku on DigitalOcean (python-3.13-uv build image)
- Stateless — no database, env var config
- uv for dependency management

## Repo Layout

```
supply-chain-monkey/
  appliku.yml
  pyproject.toml
  uv.lock
  src/py/
    scm/
      __init__.py
      models.py            # shared contract
      client.py            # HTTP client library
      server/
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
          stream.py
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
- Build image: python-3.13-uv (managed, not custom Dockerfile)
- App binds to 0.0.0.0:8000
- All credentials and tokens set as env vars in Appliku dashboard
- Default branch on GitHub is `production`

## Local Development

```bash
cp .env.template .env
# fill in SCM_SERVICE_TOKEN and provider credentials

uv sync
PYTHONPATH=src/py uv run uvicorn scm.server.main:app --reload --env-file .env
```

## Testing

```bash
uv run pytest
```
