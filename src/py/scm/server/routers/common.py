"""Shared helpers for routers."""

from scm.models import SupplierType
from ..settings import settings


RATE_LIMIT_RESPONSE_HEADERS = {
    "limit": "X-RateLimit-Limit",
    "remaining": "X-RateLimit-Remaining",
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


def rate_limit_from_supplier(client) -> dict[str, int] | None:
    status = getattr(client, "rate_limit_status", None)
    if callable(status):
        status = status()
    if not isinstance(status, dict):
        return None

    result: dict[str, int] = {}
    for key in RATE_LIMIT_RESPONSE_HEADERS:
        value = status.get(key)
        if isinstance(value, int):
            result[key] = value
    return result or None


def apply_rate_limit_headers(response, envelope) -> None:
    rate_limit = getattr(envelope, "rate_limit", None)
    if not isinstance(rate_limit, dict):
        return
    for key, header_name in RATE_LIMIT_RESPONSE_HEADERS.items():
        value = rate_limit.get(key)
        if isinstance(value, int):
            response.headers[header_name] = str(value)
