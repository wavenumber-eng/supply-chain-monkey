# ADR-011: Appliku Runtime Dependency Baseline

## Status

Accepted.

## Decision

The Appliku deployment uses the managed `python-3.13-uv` build image.

`pyproject.toml` keeps:

```toml
[tool.uv]
package = false
default-groups = []
```

Base project dependencies include the runtime service dependencies required by
the managed `uv sync --frozen` path:

- Pydantic
- Requests
- FastAPI
- Uvicorn

Development-only tools stay in the `dev` dependency group.

The project may declare `readme = "README.md"` for PyPI metadata. The managed
Appliku dependency sync remains safe because the project itself is not installed
while `package = false`.

## Policy

`appliku.yml` remains on `build_image: python-3.13-uv` unless a full Dockerfile
deployment cycle is intentionally tested. If `build_image: dockerfile` is
selected, the Dockerfile, docs, and L99 Appliku tests must change together.

## Consequences

- Appliku can install runtime dependencies without dev tools.
- `PYTHONPATH=/code/src/py` remains the runtime import mechanism.
- The inactive Dockerfile is a controlled fallback, not the active deployment
  contract.
