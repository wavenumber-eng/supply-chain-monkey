"""Detail endpoint — get full part info by supplier part number."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, Query, Response

from scm.models import PARAMETER_FIELD_NAMES, SUPPLIER_LOOKUP, ServiceEnvelope
from ..auth import verify_token
from ..models import part_response_from_info
from ..providers.base import create_supplier
from .common import apply_rate_limit_headers, get_supplier_credentials, rate_limit_from_supplier

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])

_executor = ThreadPoolExecutor(max_workers=4)


def _do_detail(supplier_key: str, part: str, include_raw: bool) -> ServiceEnvelope:
    """Synchronous detail lookup — runs in thread pool."""
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
        result = client.get_part_details(part)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        log.warning("Detail failed for %s on %s: %s", part, supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            rate_limit=rate_limit_from_supplier(client),
            error=str(exc),
        )
    latency = int((time.monotonic() - t0) * 1000)
    rate_limit = rate_limit_from_supplier(client)

    if result is None:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            rate_limit=rate_limit,
            data=None,
        )

    part_data = part_response_from_info(result, include_raw=include_raw)
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        rate_limit=rate_limit,
        data=part_data.model_dump(),
    )


@router.get("/detail")
async def detail(
    response: Response,
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    part: str = Query(..., description="Supplier part number (e.g., C2870085, 296-xxx-ND)"),
    include_raw: bool = Query(False, description="Include extra_data in response"),
):
    supplier_key = supplier.strip().lower()
    if supplier_key not in SUPPLIER_LOOKUP:
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier,
            error=f"Unknown supplier: {supplier}. Valid: {', '.join(SUPPLIER_LOOKUP)}",
        )

    loop = asyncio.get_event_loop()
    envelope = await loop.run_in_executor(
        _executor, _do_detail, supplier_key, part, include_raw
    )
    apply_rate_limit_headers(response, envelope)
    return envelope
