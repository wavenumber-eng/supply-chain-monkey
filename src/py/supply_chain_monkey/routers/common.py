"""Shared helpers for routers."""

from ..providers.base import SupplierType, create_supplier
from ..settings import settings

SUPPLIER_LOOKUP = {s.value.lower(): s for s in SupplierType}

# Maps supplier type to the Part parameter field name consumers write back to
PARAMETER_FIELD_NAMES = {
    SupplierType.JLCPCB: "JLCPCB Part #",
    SupplierType.LCSC: "LCSC Part #",
    SupplierType.DIGIKEY: "Digikey Part #",
    SupplierType.MOUSER: "Mouser Part #",
}


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
