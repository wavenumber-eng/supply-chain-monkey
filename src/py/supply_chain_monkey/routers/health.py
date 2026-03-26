"""Health and provider status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..auth import verify_token
from ..providers.base import IMPLEMENTED_SUPPLIERS, SupplierType
from ..settings import settings

router = APIRouter(prefix="/v1")

_VERSION = "1.0.0"

# Monkey ASCII art — dots are replaced with spaces by JS
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
    """Build the HTML status page."""
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
        provider_rows += f"""
                <div class="status-row">
                    <span class="status-label">{st.value}</span>
                    <span class="status-value">{backend}</span>
                    <span class="status-value {css_class}">{status_text}</span>
                </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>supply-chain-monkey</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-dark: #1a1a1a;
            --bg-panel: #242424;
            --bg-input: #2d2d2d;
            --border: #3d3d3d;
            --amber: #ffb000;
            --amber-dim: #cc8800;
            --amber-glow: rgba(255, 176, 0, 0.3);
            --text: #e0e0e0;
            --text-dim: #808080;
            --green: #00ff00;
            --red: #ff4444;
        }}

        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.4;
        }}

        .container {{
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
        }}

        .panel {{
            background: var(--bg-panel);
            border: 1px solid var(--border);
            margin-bottom: 10px;
        }}

        .panel-header {{
            background: var(--bg-input);
            padding: 6px 10px;
            border-bottom: 1px solid var(--border);
            color: var(--amber);
        }}

        .panel-content {{
            padding: 12px;
        }}

        .monkey-container {{
            padding: 10px;
            color: var(--amber);
            text-shadow: 0 0 10px var(--amber-glow);
            text-align: center;
        }}

        .monkey-art {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 8px;
            line-height: 1.1;
            display: inline-block;
            text-align: left;
            white-space: pre;
        }}

        .title {{
            color: var(--amber);
            font-size: 14px;
            margin-top: 6px;
            letter-spacing: 2px;
        }}

        .status-row {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px solid #2a2a2a;
        }}

        .status-row:last-child {{
            border-bottom: none;
        }}

        .status-label {{
            color: var(--text-dim);
            min-width: 120px;
        }}

        .status-value {{
            color: var(--amber);
            min-width: 100px;
            text-align: right;
        }}

        .status-value.ok {{
            color: var(--green);
        }}

        .status-value.error {{
            color: var(--red);
        }}

        .footer {{
            color: var(--text-dim);
            font-size: 11px;
            text-align: center;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="panel">
            <div class="monkey-container">
                <pre class="monkey-art">{_MONKEY_ART}</pre>
                <div class="title">SUPPLY CHAIN MONKEY</div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">SERVICE</div>
            <div class="panel-content">
                <div class="status-row">
                    <span class="status-label">status</span>
                    <span class="status-value ok">running</span>
                </div>
                <div class="status-row">
                    <span class="status-label">version</span>
                    <span class="status-value">{_VERSION}</span>
                </div>
                <div class="status-row">
                    <span class="status-label">timestamp</span>
                    <span class="status-value">{now}</span>
                </div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">PROVIDERS</div>
            <div class="panel-content">{provider_rows}
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">API</div>
            <div class="panel-content">
                <div class="status-row">
                    <span class="status-label">GET /v1/health</span>
                    <span class="status-value">no auth</span>
                </div>
                <div class="status-row">
                    <span class="status-label">GET /v1/providers/status</span>
                    <span class="status-value">bearer token</span>
                </div>
                <div class="status-row">
                    <span class="status-label">GET /v1/search</span>
                    <span class="status-value">bearer token</span>
                </div>
                <div class="status-row">
                    <span class="status-label">GET /v1/detail</span>
                    <span class="status-value">bearer token</span>
                </div>
            </div>
        </div>

        <div class="footer">{now}</div>
    </div>
    <script>
        const monkey = document.querySelector('.monkey-art');
        monkey.innerHTML = monkey.textContent.replace(/\\./g, ' ');
    </script>
</body>
</html>"""


@router.get("/health")
async def health():
    """Basic health check. No auth required."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
async def status_page():
    """Visual status page at the root."""
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
