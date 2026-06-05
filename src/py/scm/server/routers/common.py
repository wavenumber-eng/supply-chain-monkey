"""Shared helpers for routers."""

from scm.models import SupplierType
from ..settings import settings


def get_supplier_credentials(supplier_type: SupplierType) -> dict:
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
