"""Detail endpoint — get full part info by supplier part number."""

import logging
import time

from fastapi import APIRouter, Depends, Query

from scm.models import PARAMETER_FIELD_NAMES, SUPPLIER_LOOKUP, ServiceEnvelope
from ..auth import verify_token
from ..models import part_response_from_info
from ..providers.base import create_supplier
from .common import get_supplier_credentials

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])


@router.get("/detail")
async def detail(
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    part: str = Query(..., description="Supplier part number (e.g., C2870085, 296-xxx-ND)"),
    include_raw: bool = Query(False, description="Include extra_data in response"),
):
    supplier_key = supplier.strip().lower()
    supplier_type = SUPPLIER_LOOKUP.get(supplier_key)

    if supplier_type is None:
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier,
            error=f"Unknown supplier: {supplier}. Valid: {', '.join(SUPPLIER_LOOKUP)}",
        )

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
            error=str(exc),
        )
    latency = int((time.monotonic() - t0) * 1000)

    if result is None:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            data=None,
        )

    part_data = part_response_from_info(result, include_raw=include_raw)
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        data=part_data.model_dump(),
    )
