"""SSE streaming search endpoint — results pushed per provider as they complete."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from scm.models import (
    PARAMETER_FIELD_NAMES,
    SUPPLIER_LOOKUP,
    SUPPLIERS,
    ServiceEnvelope,
)
from ..models import part_response_from_info
from ..providers.base import create_supplier
from .common import get_supplier_credentials

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")

# Thread pool for running sync provider calls without blocking the event loop
_executor = ThreadPoolExecutor(max_workers=8)

MIN_MPN_LENGTH = 3
DEFAULT_MAX_RESULTS = 10
DEFAULT_TIMEOUT = 15.0


def _search_provider_sync(
    supplier_key: str, mpn: str, max_results: int, include_raw: bool
) -> str:
    """Run a single provider search synchronously (called from thread pool).

    Returns a JSON string ready to be sent as an SSE event.
    """
    supplier_type = SUPPLIER_LOOKUP[supplier_key]
    field_name = PARAMETER_FIELD_NAMES.get(supplier_type, "")
    creds = get_supplier_credentials(supplier_type)

    try:
        client = create_supplier(supplier_type, **creds)
    except Exception as exc:
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            error=f"Supplier not available: {exc}",
        ).model_dump_json()

    t0 = time.monotonic()
    try:
        results = client.search_by_mpn(mpn, max_results=max_results)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            error=str(exc),
        ).model_dump_json()

    latency = int((time.monotonic() - t0) * 1000)

    if not results:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            data=[],
        ).model_dump_json()

    # Limit results
    if len(results) > max_results:
        results = results[:max_results]

    parts = []
    for r in results:
        try:
            parts.append(part_response_from_info(r, include_raw=include_raw))
        except Exception as exc:
            log.warning("Failed to convert result %s: %s", r.supplier_part_number, exc)
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        data=[p.model_dump() for p in parts],
    ).model_dump_json()


def _verify_token(token: str) -> bool:
    """Check bearer token."""
    from ..settings import settings
    return bool(settings.service_token and token == settings.service_token)


@router.get("/search/stream")
async def search_stream(
    mpn: str = Query(..., description="Manufacturer part number"),
    token: str = Query("", description="Bearer token"),
    max_results: int = Query(DEFAULT_MAX_RESULTS, description="Max results per provider"),
    timeout: float = Query(DEFAULT_TIMEOUT, description="Per-provider timeout in seconds"),
    include_raw: bool = Query(False, description="Include extra_data"),
    suppliers: str = Query("", description="Comma-separated supplier list (default: all)"),
):
    """Stream search results via Server-Sent Events.

    Each provider's results are pushed as a separate SSE event as they complete.
    The stream ends with a {"done": true} event.
    """
    if not _verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    if len(mpn.strip()) < MIN_MPN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"MPN must be at least {MIN_MPN_LENGTH} characters",
        )

    # Determine which suppliers to search
    if suppliers.strip():
        target_suppliers = [s.strip().lower() for s in suppliers.split(",") if s.strip().lower() in SUPPLIER_LOOKUP]
    else:
        target_suppliers = list(SUPPLIERS)

    if not target_suppliers:
        raise HTTPException(status_code=400, detail="No valid suppliers specified")

    async def generate():
        loop = asyncio.get_event_loop()

        # Launch all provider searches concurrently in the thread pool.
        # Each task wraps its result with the supplier key so we can
        # identify which provider completed.
        async def _run_one(supplier_key: str) -> tuple[str, str]:
            result_json = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    _search_provider_sync,
                    supplier_key,
                    mpn.strip(),
                    max_results,
                    include_raw,
                ),
                timeout=timeout,
            )
            return supplier_key, result_json

        pending = {asyncio.ensure_future(_run_one(sk)): sk for sk in target_suppliers}

        while pending:
            done, _ = await asyncio.wait(pending.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                supplier_key = pending.pop(task)
                try:
                    _, result_json = task.result()
                    yield f"data: {result_json}\n\n"
                except asyncio.TimeoutError:
                    supplier_type = SUPPLIER_LOOKUP[supplier_key]
                    field_name = PARAMETER_FIELD_NAMES.get(supplier_type, "")
                    timeout_envelope = ServiceEnvelope(
                        status="provider_error",
                        supplier=supplier_type.value,
                        parameter_field_name=field_name,
                        provider_latency_ms=int(timeout * 1000),
                        error=f"Search timed out after {timeout}s",
                    )
                    yield f"data: {timeout_envelope.model_dump_json()}\n\n"
                except Exception as exc:
                    supplier_type = SUPPLIER_LOOKUP.get(supplier_key)
                    error_envelope = ServiceEnvelope(
                        status="provider_error",
                        supplier=supplier_type.value if supplier_type else supplier_key,
                        error=str(exc),
                    )
                    yield f"data: {error_envelope.model_dump_json()}\n\n"

        yield 'data: {"done": true}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
