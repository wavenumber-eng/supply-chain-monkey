"""Health and provider status endpoints."""

from fastapi import APIRouter, Depends

from ..auth import verify_token
from ..providers.base import IMPLEMENTED_SUPPLIERS, SupplierType
from ..settings import settings

router = APIRouter(prefix="/v1")


@router.get("/health")
async def health():
    """Basic health check. No auth required."""
    return {"status": "ok"}


@router.get("/providers/status", dependencies=[Depends(verify_token)])
async def providers_status():
    """Report which providers are configured (have credentials)."""
    statuses = {}
    for st in IMPLEMENTED_SUPPLIERS:
        if st == SupplierType.JLCPCB:
            # Scraper needs no credentials; API is optional
            statuses[st.value] = {
                "configured": True,
                "backend": "hybrid" if settings.jlcpcb_app_id else "scraper",
            }
        elif st == SupplierType.LCSC:
            statuses[st.value] = {"configured": True, "backend": "scraper"}
        elif st == SupplierType.DIGIKEY:
            statuses[st.value] = {
                "configured": bool(settings.digikey_client_id and settings.digikey_client_secret),
            }
        elif st == SupplierType.MOUSER:
            statuses[st.value] = {
                "configured": bool(settings.mouser_api_key),
            }
    return {"providers": statuses}
