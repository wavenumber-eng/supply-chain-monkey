FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.13-slim

COPY --from=uv /uv /usr/local/bin/

WORKDIR /code

# Install deps first (cached layer) — skip installing the project itself
COPY ./code/pyproject.toml ./code/uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-install-project --no-dev

# Copy source and install the project
COPY ./code/ .
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev
