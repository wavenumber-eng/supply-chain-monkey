"""
Application settings loaded from environment variables.

In production, Appliku injects these from its dashboard.
For local dev, use `uvicorn --env-file .env` or load a .env file before starting.
"""

import os


class Settings:
    """Single source of truth for all configuration."""

    # Service auth
    service_token: str = os.environ.get("SCM_SERVICE_TOKEN", "")

    # JLCPCB
    jlcpcb_app_id: str = os.environ.get("JLCPCB_APP_ID", "")
    jlcpcb_access_key: str = os.environ.get("JLCPCB_ACCESS_KEY", "")
    jlcpcb_secret_key: str = os.environ.get("JLCPCB_SECRET_KEY", "")

    # Digikey
    digikey_client_id: str = os.environ.get("DIGIKEY_CLIENT_ID", "")
    digikey_client_secret: str = os.environ.get("DIGIKEY_CLIENT_SECRET", "")

    # Mouser
    mouser_api_key: str = os.environ.get("MOUSER_API_KEY", "")

    # Optional Claude AI fallback
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")


settings = Settings()
