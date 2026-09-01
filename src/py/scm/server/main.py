"""FastAPI application entry point."""

import json
import logging
from functools import lru_cache
from importlib import resources
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse

from scm import __version__
from .routers import detail, health, search, spn, stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="supply-chain-monkey", version=__version__)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(spn.router)
app.include_router(detail.router)
app.include_router(stream.router)


@lru_cache(maxsize=1)
def _typespec_openapi() -> dict[str, Any]:
    """Load the packaged TypeSpec-generated OpenAPI authority once."""

    resource = resources.files("scm.generated.v1.resources").joinpath("openapi.json")
    return json.loads(resource.read_text(encoding="utf-8"))


@app.get("/openapi-typespec.json", include_in_schema=False)
async def typespec_openapi() -> dict[str, Any]:
    """Return the canonical TypeSpec-generated OpenAPI document."""

    return _typespec_openapi()


@app.get("/docs/typespec", include_in_schema=False)
async def typespec_swagger() -> HTMLResponse:
    """Render the canonical TypeSpec OpenAPI document in local Swagger UI."""

    return get_swagger_ui_html(
        openapi_url="/openapi-typespec.json",
        title="Supply Chain Monkey TypeSpec API",
    )


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the status page."""
    return RedirectResponse(url="/v1/")
