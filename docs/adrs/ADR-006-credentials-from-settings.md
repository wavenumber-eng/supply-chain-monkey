# ADR-006: Credentials Loaded from Settings, Not Module Import

## Status

Proposed

## Context

Currently, `digikey_supplier.py` and `mouser_supplier.py` call `ensure_env_loaded()`
at module import time. This scans the filesystem for `.env` files and sets
`os.environ` as a side effect of importing the module.

In a service context this is wrong:

- The service gets env vars from the container runtime (Appliku dashboard)
- Scanning for `.env` files is a local dev concern, not a production behavior
- Side effects on import make testing harder
- Multiple modules racing to load `.env` is fragile

## Decision

- Remove `env.py` and all `ensure_env_loaded()` calls from provider modules
- Create `settings.py` that reads all configuration from `os.environ` once at startup
- Provider instances receive credentials from settings, not from `os.environ` directly
- For local development, use a `.env` file loaded by uvicorn or a wrapper script

```python
# settings.py
import os

class Settings:
    digikey_client_id: str = os.environ.get("DIGIKEY_CLIENT_ID", "")
    digikey_client_secret: str = os.environ.get("DIGIKEY_CLIENT_SECRET", "")
    mouser_api_key: str = os.environ.get("MOUSER_API_KEY", "")
    jlcpcb_app_id: str = os.environ.get("JLCPCB_APP_ID", "")
    jlcpcb_access_key: str = os.environ.get("JLCPCB_ACCESS_KEY", "")
    jlcpcb_secret_key: str = os.environ.get("JLCPCB_SECRET_KEY", "")
    service_token: str = os.environ.get("SCM_SERVICE_TOKEN", "")
```

Provider instantiation happens at app startup using these settings.

## Consequences

- No filesystem scanning in production
- Single source of truth for all configuration
- Providers are easier to test (pass credentials explicitly)
- Local dev uses `--env-file .env` with uvicorn or a dotenv loader in dev only
- `env.py` is removed from the codebase
