# ADR-011: Appliku Runtime Dependency Baseline

## Status

Accepted

## Context

Appliku's managed Python uv image copies `pyproject.toml` and `uv.lock` before
copying source, then runs `uv sync --frozen`. This repo also keeps
`[tool.uv] package = false` so the source package is not built during that
manifest-only dependency install.

The previous dependency shape placed FastAPI, Uvicorn, and Requests in optional
extras and the development group. That worked only because uv installed the
default development group during the managed build. It made production depend on
development dependency behavior and made the inactive Dockerfile path diverge.

## Decision

- Keep `[tool.uv] package = false`.
- Set `[tool.uv] default-groups = []`.
- Put runtime service dependencies in `[project.dependencies]`: Pydantic,
  Requests, FastAPI, and Uvicorn.
- Keep test, lint, type, build, Rack, and optional AI dependencies out of the
  managed production dependency sync unless explicitly requested.
- Keep `appliku.yml` on `build_image: python-3.13-uv` until a full custom
  Dockerfile deployment cycle is intentionally tested.

## Consequences

- The managed Appliku build can install runtime dependencies without dev tools.
- `PYTHONPATH=/code/src/py` remains the runtime import mechanism.
- The custom Dockerfile can use `uv sync --frozen --no-dev` if it is selected in
  `appliku.yml` later.
- Consumers still install the `scm` package through Hatchling when using a path
  or git dependency.
