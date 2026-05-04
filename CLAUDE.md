# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Directives

- No emojis in code, docs, or commit messages.
- No marketing language such as "production ready", "enterprise-grade", or
  "battle-tested".
- Be factual and direct about what works and what does not.
- Short, simple commit messages. No fluff. No `Co-Authored-By` lines.
- Place temporary/intermediate files in `/temp`, which is gitignored.
- All decisions about structure, organization, or API changes must have an ADR
  in `docs/adrs/` before implementation.

## Project

`supply-chain-monkey` is a standalone FastAPI service for querying electronic
component suppliers: JLCPCB, LCSC, Digikey, and Mouser. It centralizes vendor
credentials and provider routing behind an internal HTTP API.

This repo is intentionally reusable across deployments. Do not hardcode a
company deployment URL in source; configure service URLs through environment or
consumer settings.

The repo contains three layers:

- `scm.models`: shared contract with Pydantic models, enums, and supplier
  constants.
- `scm.client`: HTTP client library for consumers.
- `scm.server`: FastAPI server, provider adapters, and routers.

## Deployment Rules

Do not change the build/deploy approach without testing a full Appliku deploy
cycle.

### pyproject.toml must have both `[build-system]` and `package = false`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
sources = ["src/py"]

[tool.hatch.build.targets.wheel]
packages = ["src/py/scm"]

[tool.uv]
package = false
```

Both are required:

- `package = false`: tells Appliku's `uv sync --frozen` to skip building the
  project during dependency resolution. `PYTHONPATH` handles imports at runtime.
- `[build-system]`: allows consumers to install `scm` as a proper package via
  path or git reference.

### appliku.yml must use the managed build image

```yaml
build_settings:
  build_image: python-3.13-uv
  container_port: 8000

services:
  web:
    command: bash -c 'PYTHONPATH=/code/src/py uvicorn scm.server.main:app --host 0.0.0.0 --port 8000'
```

Do not use `build_image: dockerfile`. Custom Dockerfiles have context path
issues with Appliku's build system.

### The web command must use `bash -c` with PYTHONPATH

Since `package = false`, the `scm` module is not installed in site-packages.
`PYTHONPATH=/code/src/py` makes it importable. The `bash -c '...'` wrapper is
required because Docker exec mode cannot handle inline env var assignment.

### Do not add `readme = "README.md"` to pyproject.toml

Hatchling validates it during dependency resolution, before source is copied.

### Consumers install scm as a package via path or git

Despite `package = false` in this repo, consumers install `scm` normally. The
`[build-system]` allows hatchling to build a wheel when another project depends
on it.

## Stack

- Python 3.13, FastAPI, uvicorn
- Deployable through Appliku on the `python-3.13-uv` build image
- Stateless; no database, env var config
- uv for dependency management

## Repo Layout

```text
supply-chain-monkey/
  appliku.yml
  pyproject.toml
  uv.lock
  src/py/scm/
    __init__.py
    models.py
    client.py
    server/
      main.py
      settings.py
      auth.py
      models.py
      templates/
      routers/
      providers/
  tests/
  docs/
```

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
