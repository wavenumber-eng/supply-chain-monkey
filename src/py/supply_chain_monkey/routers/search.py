"""Search endpoint — find parts by MPN across a single supplier."""

import logging
import time

from fastapi import APIRouter, Depends, Query

from ..auth import verify_token
from ..models import PartResponse, ServiceEnvelope
from ..providers.base import create_supplier
from .common import SUPPLIER_LOOKUP, PARAMETER_FIELD_NAMES, get_supplier_credentials

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])


@router.get("/search")
async def search(
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    mpn: str = Query(..., description="Manufacturer part number"),
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
        results = client.search_by_mpn(mpn)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        log.warning("Search failed for %s on %s: %s", mpn, supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            error=str(exc),
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

    parts = [PartResponse.from_supplier_part_info(r, include_raw=include_raw) for r in results]
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        data=[p.model_dump() for p in parts],
    )
