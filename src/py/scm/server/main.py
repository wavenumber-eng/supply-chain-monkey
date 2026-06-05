"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from scm import __version__
from .routers import detail, health, search, stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="supply-chain-monkey", version=__version__)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(detail.router)
app.include_router(stream.router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the status page."""
    return RedirectResponse(url="/v1/")
