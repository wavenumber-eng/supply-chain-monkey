"""SPN endpoints for exact supplier part number lookups."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, Query

from scm.models import (
    PARAMETER_FIELD_NAMES,
    SUPPLIER_LOOKUP,
    ServiceEnvelope,
    SpnBatchEnvelope,
    SpnBatchItem,
    SpnBatchRequest,
    SpnEnvelope,
)
from ..auth import verify_token
from ..contract_response import contract_response
from ..models import part_response_from_info
from ..providers.base import create_supplier, get_default_supplier_capabilities
from .common import get_supplier_credentials

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_token)])

_executor = ThreadPoolExecutor(max_workers=4)


def _batch_status(items: list[SpnBatchItem]) -> str:
    statuses = {item.status for item in items}
    if not statuses:
        return "not_found"
    if statuses == {"ok"}:
        return "ok"
    if statuses == {"not_found"}:
        return "not_found"
    if statuses == {"provider_error"}:
        return "provider_error"
    return "partial"


def _do_spn(supplier_key: str, spn: str, include_raw: bool) -> ServiceEnvelope:
    """Synchronous exact SPN lookup, run in the thread pool."""
    supplier_type = SUPPLIER_LOOKUP[supplier_key]
    field_name = PARAMETER_FIELD_NAMES.get(supplier_type, "")
    capabilities = get_default_supplier_capabilities(supplier_type)
    creds = get_supplier_credentials(supplier_type)

    try:
        client = create_supplier(supplier_type, **creds)
        capabilities = client.capabilities
    except Exception as exc:
        log.warning("Failed to create %s supplier: %s", supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_capabilities=capabilities,
            error=f"Supplier not available: {exc}",
        )

    t0 = time.monotonic()
    try:
        result = client.get_part_details(spn)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        log.warning("SPN lookup failed for %s on %s: %s", spn, supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            provider_capabilities=capabilities,
            rate_limit=client.get_rate_limit_snapshot(),
            error=str(exc),
        )
    latency = int((time.monotonic() - t0) * 1000)

    if result is None:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_latency_ms=latency,
            provider_capabilities=capabilities,
            rate_limit=client.get_rate_limit_snapshot(),
            data=None,
        )

    part_data = part_response_from_info(result, include_raw=include_raw)
    return ServiceEnvelope(
        status="ok",
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        provider_capabilities=capabilities,
        rate_limit=client.get_rate_limit_snapshot(),
        data=part_data.model_dump(),
    )


def _do_spn_batch(request: SpnBatchRequest) -> ServiceEnvelope:
    """Synchronous exact SPN batch lookup, run in the thread pool."""
    supplier_key = request.supplier.strip().lower()
    supplier_type = SUPPLIER_LOOKUP[supplier_key]
    field_name = PARAMETER_FIELD_NAMES.get(supplier_type, "")
    capabilities = get_default_supplier_capabilities(supplier_type)
    creds = get_supplier_credentials(supplier_type)

    try:
        client = create_supplier(supplier_type, **creds)
        capabilities = client.capabilities
    except Exception as exc:
        log.warning("Failed to create %s supplier: %s", supplier_type.value, exc)
        return ServiceEnvelope(
            status="provider_error",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_capabilities=capabilities,
            error=f"Supplier not available: {exc}",
        )

    cleaned_spns = [spn.strip() for spn in request.spns if spn and spn.strip()]
    if not cleaned_spns:
        return ServiceEnvelope(
            status="not_found",
            supplier=supplier_type.value,
            parameter_field_name=field_name,
            provider_capabilities=capabilities,
            data=[],
        )

    batch_size = max(1, capabilities.max_spn_batch_size)
    items: list[SpnBatchItem] = []

    t0 = time.monotonic()
    for start in range(0, len(cleaned_spns), batch_size):
        chunk = cleaned_spns[start : start + batch_size]
        try:
            chunk_results = client.get_part_details_batch(chunk)
        except Exception as exc:
            log.warning(
                "SPN batch lookup failed for %s on %s: %s",
                chunk,
                supplier_type.value,
                exc,
            )
            for spn in chunk:
                items.append(SpnBatchItem(spn=spn, status="provider_error", error=str(exc)))
            continue

        for spn in chunk:
            part = chunk_results.get(spn)
            if part is None:
                items.append(SpnBatchItem(spn=spn, status="not_found"))
                continue
            try:
                part_response = part_response_from_info(
                    part,
                    include_raw=request.include_raw,
                )
            except Exception as exc:
                log.warning("Failed to convert SPN result %s: %s", spn, exc)
                items.append(SpnBatchItem(spn=spn, status="provider_error", error=str(exc)))
                continue
            items.append(SpnBatchItem(spn=spn, status="ok", part=part_response))

    latency = int((time.monotonic() - t0) * 1000)
    return ServiceEnvelope(
        status=_batch_status(items),
        supplier=supplier_type.value,
        parameter_field_name=field_name,
        provider_latency_ms=latency,
        provider_capabilities=capabilities,
        rate_limit=client.get_rate_limit_snapshot(),
        data=[item.model_dump() for item in items],
    )


@router.get("/spn", response_model=SpnEnvelope)
async def spn(
    supplier: str = Query(..., description="Supplier name (jlcpcb, lcsc, digikey, mouser)"),
    spn: str = Query(..., description="Exact supplier part number"),
    include_raw: bool = Query(False, description="Include extra_data in response"),
):
    supplier_key = supplier.strip().lower()
    if supplier_key not in SUPPLIER_LOOKUP:
        result = ServiceEnvelope(
            status="provider_error",
            supplier=supplier,
            error=f"Unknown supplier: {supplier}. Valid: {', '.join(SUPPLIER_LOOKUP)}",
        )
    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, _do_spn, supplier_key, spn.strip(), include_raw
        )
    return contract_response("SpnEnvelope", SpnEnvelope, result)


@router.post("/spn/batch", response_model=SpnBatchEnvelope)
async def spn_batch(request: SpnBatchRequest):
    supplier_key = request.supplier.strip().lower()
    if supplier_key not in SUPPLIER_LOOKUP:
        result = ServiceEnvelope(
            status="provider_error",
            supplier=request.supplier,
            error=(f"Unknown supplier: {request.supplier}. Valid: {', '.join(SUPPLIER_LOOKUP)}"),
        )
    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _do_spn_batch, request)
    return contract_response("SpnBatchEnvelope", SpnBatchEnvelope, result)
