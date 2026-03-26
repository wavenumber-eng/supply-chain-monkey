"""Health and provider status endpoints."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..auth import verify_token
from ..providers.base import IMPLEMENTED_SUPPLIERS, SupplierType
from ..settings import settings

router = APIRouter(prefix="/v1")

_VERSION = "1.0.0"
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
            f'</div>'
        )

    template = (_TEMPLATE_DIR / "status.html").read_text(encoding="utf-8")
    return (
        template
        .replace("{{MONKEY_ART}}", _MONKEY_ART)
        .replace("{{VERSION}}", _VERSION)
        .replace("{{TIMESTAMP}}", now)
        .replace("{{PROVIDER_ROWS}}", provider_rows)
    )


@router.get("/health")
async def health():
    """Basic health check. No auth required."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
async def status_page():
    """Visual status page with test panel."""
    return _status_page_html()


@router.get("/providers/status", dependencies=[Depends(verify_token)])
async def providers_status():
    """Report which providers are configured (have credentials)."""
    statuses = {}
    for st in IMPLEMENTED_SUPPLIERS:
        if st == SupplierType.JLCPCB:
            statuses[st.value] = {
                "configured": True,
                "backend": "hybrid" if settings.jlcpcb_app_id else "scraper",
            }
        elif st == SupplierType.LCSC:
            statuses[st.value] = {"configured": True, "backend": "api"}
        elif st == SupplierType.DIGIKEY:
            statuses[st.value] = {
                "configured": bool(settings.digikey_client_id and settings.digikey_client_secret),
            }
        elif st == SupplierType.MOUSER:
            statuses[st.value] = {
                "configured": bool(settings.mouser_api_key),
            }
    return {"providers": statuses}
