FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.13-slim

# Optional Appliku custom-Dockerfile path. This file is inactive while
# appliku.yml uses build_image: python-3.13-uv.
COPY --from=uv /uv /usr/local/bin/

WORKDIR /code

# Install deps only (no project build — source isn't here yet)
COPY ./code/pyproject.toml ./code/uv.lock /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-install-project --no-dev

# Copy source and refresh the environment without development groups.
COPY ./code/ /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev

# Copy env (Appliku provides this)
COPY ./env/ /env/
