"""Health and provider status endpoints."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from scm import __version__
from scm.models import HealthResponse, ProviderStatusResponse, SupplierType
from ..auth import CONTRACT_ERROR_RESPONSES, verify_token
from ..contract_response import contract_response
from ..providers.base import (
    IMPLEMENTED_SUPPLIERS,
    create_supplier,
    get_default_supplier_capabilities,
)
from ..settings import settings
from .common import get_supplier_credentials

router = APIRouter(prefix="/v1")

_VERSION = __version__
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

_MONKEY_ART = r"""
..........▓▓▓▓▓▓▓▓▓▓..............
........▓▓▓▓▓▓▓▓▓▓▓▓▓▓............
......▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓..........
....▓▓▓▓░░░░░░▓▓░░░░░░▓▓▓▓........
░░░░▓▓░░░░░░░░░░░░░░░░░░▓▓░░░░....
░░░░▓▓░░██..░░░░░░██..░░▓▓░░░░....
..░░▓▓░░████░░░░░░████░░▓▓░░......
....▓▓░░░░░░░░░░░░░░░░░░▓▓........
......▓▓░░░░░░░░░░░░░░▓▓..........
........▓▓▓▓░░░░░░▓▓▓▓............
............▓▓▓▓▓▓..........░░....
..........▓▓▓▓▓▓▓▓▓▓......▓▓......
..........▓▓▓▓▓▓▓▓▓▓....▓▓▓▓......
........▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓........
........▓▓▓▓░░▓▓░░▓▓▓▓............
""".strip()


def _capabilities_for_status(supplier_type: SupplierType) -> dict:
    capabilities = get_default_supplier_capabilities(supplier_type)
    try:
        client = create_supplier(
            supplier_type,
            **get_supplier_credentials(supplier_type),
        )
        capabilities = client.capabilities
    except Exception:
        pass
    return capabilities.model_dump()


def _status_page_html() -> str:
    """Build the HTML status page from template."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build provider rows
    provider_rows = ""
    for st in IMPLEMENTED_SUPPLIERS:
        if st == SupplierType.JLCPCB:
            configured = True
            backend = "hybrid" if settings.jlcpcb_app_id else "scraper"
        elif st == SupplierType.LCSC:
            configured = True
            backend = "api"
        elif st == SupplierType.DIGIKEY:
            configured = bool(settings.digikey_client_id and settings.digikey_client_secret)
            backend = "api" if configured else "---"
        elif st == SupplierType.MOUSER:
            configured = bool(settings.mouser_api_key)
            backend = "api" if configured else "---"
        else:
            configured = False
            backend = "---"

        css_class = "ok" if configured else "error"
        status_text = "ready" if configured else "not configured"
        provider_rows += (
            f'<div class="status-row">'
            f'<span class="status-label">{st.value}</span>'
            f'<span class="status-value">{backend}</span>'
            f'<span class="status-value {css_class}">{status_text}</span>'
            f"</div>"
        )

    template = (_TEMPLATE_DIR / "status.html").read_text(encoding="utf-8")
    return (
        template.replace("{{MONKEY_ART}}", _MONKEY_ART)
        .replace("{{VERSION}}", _VERSION)
        .replace("{{TIMESTAMP}}", now)
        .replace("{{PROVIDER_ROWS}}", provider_rows)
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description="Return the current service health marker.",
)
async def health():
    """Basic health check. No auth required."""
    return contract_response("HealthResponse", HealthResponse, {"status": "ok"})


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="View the SCM status page",
    description="Return the human-facing SCM status and demonstration page.",
)
async def status_page():
    """Visual status page with test panel."""
    return _status_page_html()


@router.get(
    "/providers/status",
    dependencies=[Depends(verify_token)],
    response_model=ProviderStatusResponse,
    response_model_exclude_unset=True,
    responses=CONTRACT_ERROR_RESPONSES,
    summary="List provider status and capabilities",
    description="Return configuration and capabilities for every known provider.",
)
async def providers_status():
    """Report which providers are configured (have credentials)."""
    statuses = {}
    for st in IMPLEMENTED_SUPPLIERS:
        if st == SupplierType.JLCPCB:
            statuses[st.value] = {
                "configured": True,
                "backend": "hybrid" if settings.jlcpcb_app_id else "scraper",
                "capabilities": _capabilities_for_status(st),
            }
        elif st == SupplierType.LCSC:
            statuses[st.value] = {
                "configured": True,
                "backend": "api",
                "capabilities": _capabilities_for_status(st),
            }
        elif st == SupplierType.DIGIKEY:
            statuses[st.value] = {
                "configured": bool(settings.digikey_client_id and settings.digikey_client_secret),
                "capabilities": _capabilities_for_status(st),
            }
        elif st == SupplierType.MOUSER:
            statuses[st.value] = {
                "configured": bool(settings.mouser_api_key),
                "capabilities": _capabilities_for_status(st),
            }
    return contract_response(
        "ProviderStatusResponse",
        ProviderStatusResponse,
        {"providers": statuses},
    )
