"""Search endpoint — find parts by MPN across a single supplier."""

import logging
import time

from fastapi import APIRouter, Depends, Query

from ..auth import verify_token
from ..models import PartResponse, ServiceEnvelope
from ..providers.base import SupplierType, create_supplier
from ..settings import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])

_SUPPLIER_LOOKUP = {s.value.lower(): s for s in SupplierType}


def _get_supplier_credentials(supplier_type: SupplierType) -> dict:
    if supplier_type == SupplierType.JLCPCB:
        return {
            "app_id": settings.jlcpcb_app_id,
            "access_key": settings.jlcpcb_access_key,
            "secret_key": settings.jlcpcb_secret_key,
        }
    if supplier_type == SupplierType.DIGIKEY:
        return {
            "client_id": settings.digikey_client_id,
            "client_secret": settings.digikey_client_secret,
        }
    if supplier_type == SupplierType.MOUSER:
        return {"api_key": settings.mouser_api_key}
    return {}


@router.get("/search")
async def search(
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    mpn: str = Query(..., description="Manufacturer part number"),
    include_raw: bool = Query(False, description="Include extra_data in response"),
):
    supplier_key = supplier.strip().lower()
    supplier_type = _SUPPLIER_LOOKUP.get(supplier_key)

    if supplier_type is None:
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier,
            error=f"Unknown supplier: {supplier}. Valid: {', '.join(_SUPPLIER_LOOKUP)}",
        )

    creds = _get_supplier_credentials(supplier_type)

    try:
        client = create_supplier(supplier_type, **creds)
    except Exception as exc:
        log.warning("Failed to create %s supplier: %s", supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
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
            provider_latency_ms=latency,
            error=str(exc),
        )
    latency = int((time.monotonic() - t0) * 1000)

    if not results:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            provider_latency_ms=latency,
            data=[],
        )

    parts = [PartResponse.from_supplier_part_info(r, include_raw=include_raw) for r in results]
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        provider_latency_ms=latency,
        data=[p.model_dump() for p in parts],
    )
