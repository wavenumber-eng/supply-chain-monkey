"""Shared helpers for routers."""

from scm.models import ServiceErrorDetail, SupplierType
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


def error_detail_from_exception(
    exc: Exception,
    *,
    default_code: str = "provider_failure",
    default_retryable: bool = False,
) -> ServiceErrorDetail:
    """Return sanitized structured diagnostics carried by provider exceptions."""
    return ServiceErrorDetail(
        code=str(getattr(exc, "code", default_code)),
        retryable=bool(getattr(exc, "retryable", default_retryable)),
        upstream_status_code=getattr(exc, "upstream_status_code", None),
        upstream_request_id=getattr(exc, "upstream_request_id", None),
    )
