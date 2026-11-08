"""Read-only JLC account-library HTTP operations."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from scm.models import (
    AccountCapabilitiesResponse,
    AccountInventoryLookupResponse,
    AccountInventoryResponse,
    HttpErrorDetail,
)

from ..auth import CONTRACT_ERROR_RESPONSES, verify_token
from ..contract_response import contract_response
from ..providers.jlc_account import (
    MAX_SCAN_SECONDS,
    IncompleteInventoryScan,
    JLCAccountInventory,
)
from ..providers.jlc_openapi import JLCOpenAPIClient, JLCOpenAPIError
from ..settings import settings

router = APIRouter(prefix="/v1/account", responses=CONTRACT_ERROR_RESPONSES)
INVENTORY_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    502: {"model": HttpErrorDetail},
    503: {"model": HttpErrorDetail},
}


def _configured() -> bool:
    # Check the settings source; the JLC client can fall back to process env.
    return bool(
        settings.jlcpcb_app_id and settings.jlcpcb_access_key and settings.jlcpcb_secret_key
    )


def _adapter() -> JLCAccountInventory:
    if not _configured():
        raise HTTPException(status_code=503, detail="Account inventory is not configured")
    client = JLCOpenAPIClient(
        app_id=settings.jlcpcb_app_id,
        access_key=settings.jlcpcb_access_key,
        secret_key=settings.jlcpcb_secret_key,
    )
    return JLCAccountInventory(client)


@router.get(
    "/capabilities",
    response_model=AccountCapabilitiesResponse,
    summary="Get account inventory capability",
)
async def capabilities(
    _token: Annotated[str, Depends(verify_token)],
) -> AccountCapabilitiesResponse:
    """Report whether the JLC account inventory read path is configured."""
    return contract_response(
        "AccountCapabilitiesResponse",
        AccountCapabilitiesResponse,
        {"configured": _configured()},
    )


@router.get(
    "/inventory",
    response_model=AccountInventoryResponse,
    summary="List JLC account inventory",
    responses=INVENTORY_ERROR_RESPONSES,
)
async def inventory(
    _token: Annotated[str, Depends(verify_token)],
) -> AccountInventoryResponse:
    """Scan the JLC account's My Parts Lib within fixed bounds."""
    adapter = _adapter()
    try:
        result = await asyncio.wait_for(asyncio.to_thread(adapter.scan), MAX_SCAN_SECONDS)
    except (IncompleteInventoryScan, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="Inventory scan is incomplete") from exc
    except (JLCOpenAPIError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="JLC account inventory request failed") from exc
    return contract_response("AccountInventoryResponse", AccountInventoryResponse, result)


@router.get(
    "/inventory/lookup",
    response_model=AccountInventoryLookupResponse,
    summary="Look up JLC account inventory",
    responses={400: {"model": HttpErrorDetail}, **INVENTORY_ERROR_RESPONSES},
)
async def inventory_lookup(
    _token: Annotated[str, Depends(verify_token)],
    spn: str | None = Query(None),
    mpn: str | None = Query(None),
) -> AccountInventoryLookupResponse:
    """Find exact C-code or MPN matches in a bounded live JLC library scan."""
    if (spn is None) == (mpn is None) or not (spn or mpn or "").strip():
        raise HTTPException(status_code=400, detail="Provide exactly one nonempty spn or mpn")
    adapter = _adapter()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(adapter.lookup, spn=spn, mpn=mpn), MAX_SCAN_SECONDS
        )
    except (IncompleteInventoryScan, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="Inventory lookup is incomplete") from exc
    except (JLCOpenAPIError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="JLC account inventory request failed") from exc
    return contract_response(
        "AccountInventoryLookupResponse", AccountInventoryLookupResponse, result
    )
