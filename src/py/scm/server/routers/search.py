"""Search endpoint — find parts by MPN across a single supplier."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, Query

from scm.models import (
    PARAMETER_FIELD_NAMES,
    SUPPLIER_LOOKUP,
    ServiceEnvelope,
)
from ..auth import verify_token
from ..models import part_response_from_info
from ..providers.base import create_supplier
from .common import error_detail_from_exception, get_supplier_credentials

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])

_executor = ThreadPoolExecutor(max_workers=4)


def _do_search(supplier_key: str, mpn: str, include_raw: bool, max_results: int) -> ServiceEnvelope:
    """Synchronous search — runs in thread pool."""
    supplier_type = SUPPLIER_LOOKUP[supplier_key]
    field_name = PARAMETER_FIELD_NAMES.get(supplier_type, "")
    creds = get_supplier_credentials(supplier_type)

    try:
        client = create_supplier(supplier_type, **creds)
    except Exception as exc:
        log.warning("Failed to create %s supplier: %s", supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            error=f"Supplier not available: {exc}",
        )

    t0 = time.monotonic()
    try:
        results = client.search_by_mpn(mpn, max_results=max_results)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        log.warning("Search failed for %s on %s: %s", mpn, supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            error=str(exc),
            error_detail=error_detail_from_exception(exc),
        )
    latency = int((time.monotonic() - t0) * 1000)

    if not results:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            data=[],
        )

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
    )


@router.get("/search")
async def search(
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    mpn: str = Query(..., description="Manufacturer part number"),
    include_raw: bool = Query(False, description="Include extra_data in response"),
    max_results: int = Query(10, description="Max results to return"),
):
    supplier_key = supplier.strip().lower()
    if supplier_key not in SUPPLIER_LOOKUP:
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier,
            error=f"Unknown supplier: {supplier}. Valid: {', '.join(SUPPLIER_LOOKUP)}",
        )

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _do_search, supplier_key, mpn, include_raw, max_results
    )
