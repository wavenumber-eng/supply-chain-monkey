FROM ghcr.io/astral-sh/uv:0.13.4 AS uv
FROM python:3.13-slim

# Optional Appliku custom-Dockerfile path. This file is inactive while
# appliku.yml uses build_image: python-3.13-uv.
COPY --from=uv /uv /usr/local/bin/

# Refresh OS trust and pip's separate vendored bundle for the emSign incident.
# Use the fixed uv installer to upgrade pip without relying on old pip's TLS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN uv pip install --system --upgrade "pip>=26.2.2"

WORKDIR /code

# Install deps only (no project build — source isn't here yet)
COPY ./code/pyproject.toml ./code/uv.lock /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-install-project --no-dev

# Copy source and refresh the environment without development groups.
COPY ./code/ /code/
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev

# Copy env (Appliku provides this)
COPY ./env/ /env/
