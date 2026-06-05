# Deploying a FastAPI + uv project on Appliku

This guide covers deploying a FastAPI application that uses `uv` for dependency
management on Appliku (DigitalOcean). Based on the supply-chain-monkey deployment.

## Prerequisites

- A GitHub repo with your FastAPI app
- An Appliku account with a server connected
- `uv` for local development

## Repo structure

```
your-repo/
  pyproject.toml          # at repo root, required
  uv.lock                 # committed, required
  appliku.yml             # at repo root, required
  src/py/your_package/    # source code (any layout works)
    __init__.py
    main.py               # FastAPI app: `app = FastAPI()`
  tests/
```

## pyproject.toml setup

Two critical settings for Appliku compatibility:

### 1. Set `package = false`

Appliku's build image runs `uv sync --frozen` before copying your source code.
If your project is an installable package, uv tries to build it during this step
and fails because the source files aren't there yet.

```toml
[tool.uv]
package = false
default-groups = []
```

This tells uv to install dependencies, not the project itself, and prevents the
managed build image from installing development tools by default.

### 2. Do not reference README.md

If you have `readme = "README.md"` in `[project]`, hatchling will validate the
file exists during the dependency install step — before source is copied. Remove
it.

```toml
[project]
name = "your-project"
version = "0.1.0"
description = "Your description"
# NO readme = "README.md" line
requires-python = ">=3.11,<3.14"
dependencies = [
    "pydantic>=2.0",
    "requests>=2.32.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
]
```

### Full example

```toml
[project]
name = "your-project"
version = "0.1.0"
description = "Your description"
requires-python = ">=3.11,<3.14"
dependencies = [
    "pydantic>=2.0",
    "requests>=2.32.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.uv]
package = false
default-groups = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src/py"]
```

## appliku.yml

```yaml
build_settings:
  build_image: python-3.13-uv
  container_port: 8000

services:
  web:
    command: bash -c 'PYTHONPATH=/code/src/py uvicorn your_package.main:app --host 0.0.0.0 --port 8000'
```

### Important notes

**Use the managed `python-3.13-uv` build image by default.** It handles uv
installation, dependency resolution, and Docker layer caching automatically.
Custom Dockerfiles are allowed only when `appliku.yml`, Dockerfile, docs, and
L99 deployment tests are updated together and the full deploy cycle is
validated.

**Wrap the command in `bash -c '...'`.** Docker interprets the command as an
exec-style array. If you write `PYTHONPATH=/code/src/py uvicorn ...` without
`bash -c`, Docker tries to execute `PYTHONPATH=/code/src/py` as a binary and
fails with "no such file or directory."

**Bind to `0.0.0.0:8000`.** Appliku's nginx reverse proxy forwards to the
container port. Using `127.0.0.1` will not work — the container must listen on
all interfaces.

**`PYTHONPATH=/code/src/py`** is needed because the project is not pip-installed
(due to `package = false`). This tells Python where to find your source. Adjust
the path to match your source layout:

| Source layout | PYTHONPATH |
|---|---|
| `src/py/your_package/` | `/code/src/py` |
| `src/your_package/` | `/code/src` |
| `your_package/` (at repo root) | `/code` |

## FastAPI app entry point

Your `main.py` must create an `app` object:

```python
from fastapi import FastAPI

app = FastAPI(title="your-project", version="0.1.0")

# register routers, middleware, etc.
```

The uvicorn command references this as `your_package.main:app`.

## Environment variables

Set environment variables in the Appliku dashboard under the "Environment
Variables" tab. They are injected as container env vars at runtime.

Do not commit `.env` files. Use `.env.template` to document required variables:

```
# .env.template
SECRET_KEY=
DATABASE_URL=
API_KEY=
```

In your code, read from `os.environ`:

```python
import os

class Settings:
    secret_key: str = os.environ.get("SECRET_KEY", "")
    api_key: str = os.environ.get("API_KEY", "")

settings = Settings()
```

For local development, use `uvicorn --env-file .env` or load a `.env` file
manually.

## Deployment workflow

### Branch setup

Create a `production` branch for deployments:

```bash
git checkout -b production
git push -u origin production
```

In the Appliku dashboard, point the app at your repo and select the `production`
branch. Enable "Push to deploy."

### Deploy cycle

Develop on `main`, merge to `production` when ready:

```bash
git checkout production
git merge main
git push
git checkout main
```

A push to `production` triggers an automatic build and deploy.

### Verifying a deploy

Check the health endpoint (no auth needed):

```bash
curl https://your-app.applikuapp.com/v1/health
```

## How the build works

Understanding the build order helps debug failures:

1. Appliku clones your repo into `/home/app/{app-name}/code/`
2. The managed image copies `pyproject.toml` + `uv.lock` into the container
3. `uv sync --frozen` installs dependencies (source code not present yet)
4. Full source code is copied into the container
5. Container starts with your command from `appliku.yml`

This is why `package = false` matters — step 3 must succeed without source code.

## Appliku directory structure on the server

```
/home/app/{app-name}/
  code/                    # your git repo
  env/
    dot.env                # env vars in dotenv format
    envs_export.sh         # env vars as shell exports
  docker-compose.yml       # auto-generated, do not edit
```

## Custom Dockerfiles (avoid if possible)

If you must use a custom Dockerfile:

- Set `build_image: dockerfile` and `dockerfile_path: Dockerfile` in appliku.yml
- The Dockerfile lives in your repo root
- COPY paths are relative to the Docker build context
- The context path behavior is inconsistent between the `web` and `one_off`
  targets that Appliku builds — you may get `code/code/` doubling
- The two-stage install pattern with `--no-install-project` is needed:

```dockerfile
FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.13-slim

COPY --from=uv /uv /usr/local/bin/
WORKDIR /code

COPY pyproject.toml uv.lock /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-install-project --no-dev

COPY . /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev
```

Unless you have build-time requirements beyond what the managed image provides,
stick with `python-3.13-uv`.

## Troubleshooting

### "Readme file does not exist: README.md"

Remove `readme = "README.md"` from `[project]` in `pyproject.toml`.

### "No module named 'your_package'"

Either `PYTHONPATH` is wrong in the web command, or the package is not at the
expected path inside `/code/`. SSH into the server and check:

```bash
docker exec -it {app}-web-1 ls /code/src/py/
```

### "stat PYTHONPATH=/code/src/py: no such file or directory"

The web command is not wrapped in `bash -c '...'`. Docker is interpreting the
env var assignment as a binary path.

### Build fails on `uv sync --frozen`

Check that `package = false` is set under `[tool.uv]` in `pyproject.toml` and
that `uv.lock` is committed and up to date.

### 502 Bad Gateway

The app is crashing on startup. Check the Appliku runtime logs. Common causes:
- Missing required env var
- Import error (wrong PYTHONPATH)
- Port binding issue (must be 0.0.0.0, not 127.0.0.1)
