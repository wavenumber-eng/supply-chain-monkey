"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from .routers import detail, health, search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="supply-chain-monkey", version="0.1.0")

app.include_router(health.router)
app.include_router(search.router)
app.include_router(detail.router)
