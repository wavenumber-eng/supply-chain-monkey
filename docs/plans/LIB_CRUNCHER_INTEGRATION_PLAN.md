# lib_cruncher SCM Integration Plan

## Purpose

Replace lib_cruncher's direct `supply_chain_monkey` imports with HTTP calls to
the SCM service via `scm.client.SCMClient`. After this change, lib_cruncher no
longer needs vendor credentials (Digikey, Mouser, JLC) — only an SCM service
token.

## Current State

lib_cruncher (`appz/lib_cruncher`) currently:

- Imports `supply_chain_monkey` as a Python dependency from the toolz workspace
- Manages vendor credentials locally (Digikey CLIENT_ID/SECRET, Mouser API_KEY)
- Creates provider instances directly and runs parallel searches with ThreadPoolExecutor
- Serves results through its own `/api/a0/supplier/*` endpoints
- Frontend (`supplier-search.js`) calls lib_cruncher's endpoints, not SCM

Key files:

- `routers/supplier.py` — search endpoints, credential management, parallel execution
- `static/supplier-search.js` — search modal UI, variant selection
- `static/detail.js` — "Search Suppliers" button in detail panel
- `static/app.js` — credential warning for missing Digikey/Mouser keys
- `pyproject.toml` — depends on `supply-chain-monkey` via path
- `.env.template` — Digikey/Mouser/JLC/Anthropic credentials

## Target State

- lib_cruncher depends on `scm[client]` from git (shared contract + HTTP client)
- `routers/supplier.py` uses `SCMClient` for all supplier operations
- No vendor credentials in lib_cruncher — only `SCM_URL` and `SCM_TOKEN`
- Default URL: `https://scm.wavenumber.net`
- Frontend unchanged — same endpoints, same response shapes
- Users can configure the SCM token through a settings page in the UI

## No Fallback to Direct Imports

The old direct-import path will be removed entirely. If the SCM service is
unavailable, searches fail gracefully. If a developer needs local supplier
access, they can run the SCM server locally and point lib_cruncher at
`http://127.0.0.1:8000`.

## Changes Required

### 1. pyproject.toml

Replace:
```toml
supply-chain-monkey = { path = "../../toolz/supply_chain_monkey", editable = true }
```

With:
```toml
scm = { git = "https://github.com/wavenumber-eng/supply-chain-monkey.git", extras = ["client"] }
```

### 2. routers/supplier.py — Rewrite

Replace all direct supply_chain_monkey imports and provider instantiation with
SCMClient calls.

Before:
```python
from supply_chain_monkey import create_supplier, SupplierType, SupplierPartInfo
# ... credential management, ThreadPoolExecutor, etc.
```

After:
```python
from scm.client import SCMClient
from scm.models import SUPPLIERS, PARAMETER_FIELD_NAMES, SupplierType

def _get_scm_client() -> SCMClient:
    return SCMClient(
        url=os.environ.get("SCM_URL", "https://scm.wavenumber.net"),
        token=os.environ.get("SCM_TOKEN", ""),
    )
```

The `/api/a0/supplier/search/{mpn}` endpoint calls `client.search_all(mpn)`.
The `/api/a0/supplier/search/{supplier_name}/{mpn}` calls `client.search(name, mpn)`.
The `/api/a0/supplier/status` endpoint calls `client.providers_status()`.

Response conversion maps SCM's `ServiceEnvelope` / `PartResponse` to
lib_cruncher's existing `SupplierSearchResult` / `MultiSupplierSearchResponse`
to avoid changing the frontend contract.

### 3. .env.template

Remove:
```
DIGIKEY_CLIENT_ID=
DIGIKEY_CLIENT_SECRET=
MOUSER_API_KEY=
ANTHROPIC_API_KEY=
```

Add:
```
# Supply Chain Monkey service
SCM_URL=https://scm.wavenumber.net
SCM_TOKEN=
```

### 4. static/app.js

Remove the credential warning that checks for missing Digikey/Mouser keys.
Replace with a check for missing SCM_TOKEN (or leave it — the settings page
handles this).

### 5. SCM Settings Page

Add a simple settings/configuration page in lib_cruncher where a user can:

- See the current SCM_URL and whether a token is configured
- Enter or update the SCM_TOKEN
- Test the connection (hit `/v1/health` and `/v1/providers/status`)
- Persist the token to the local `.env` or `.env.local` file

This is important because:

- Users on new machines need a way to configure access without editing files
- The token can rotate without requiring a redeploy
- The settings page can show which providers are available on the server

Implementation: a new route in lib_cruncher (`/settings/scm` or similar) that
serves a small form. On submit, it writes `SCM_TOKEN=...` to `.env.local` and
reloads the settings.

### 6. Files That Do NOT Change

- `static/supplier-search.js` — talks to lib_cruncher's API, not SCM directly
- `static/detail.js` — "Search Suppliers" button unchanged
- `routers/api_a0.py` — `PARAMETER_GROUPS`, `FIELD_ALIASES` stay the same
- `data_models/cad_part.py` — field alias system stays the same

## Data Flow (After)

```
Frontend (supplier-search.js)
    |
    v
lib_cruncher /api/a0/supplier/search/{mpn}
    |
    v
SCMClient.search_all(mpn)
    |
    v  (4 parallel HTTP requests)
SCM service /v1/search?supplier=X&mpn=Y
    |
    v
Provider adapters (JLCPCB, LCSC, Digikey, Mouser)
    |
    v
ServiceEnvelope responses
    |
    v
lib_cruncher converts to MultiSupplierSearchResponse
    |
    v
Frontend renders results
```

## Migration Sequence

### Step 1: Prep (no code changes)

- Ensure appz local repo is synced with remote
- Set `SCM_URL` and `SCM_TOKEN` in lib_cruncher's `.env.local`
- Verify SCM service is reachable from the dev machine

### Step 2: Dependency Swap

- Update `pyproject.toml` to depend on `scm[client]` from git
- Run `uv sync` and verify `from scm.client import SCMClient` works

### Step 3: Rewrite supplier.py

- Replace imports
- Replace credential management with SCMClient
- Map SCM responses to lib_cruncher's existing response models
- Keep the same endpoint paths and response shapes

### Step 4: Settings Page

- Add route for SCM configuration
- Add simple HTML form for token entry
- Add connection test button
- Write token to `.env.local`

### Step 5: Clean Up

- Remove vendor credential env vars from `.env.template`
- Remove credential warning from `app.js`
- Remove any remaining `supply_chain_monkey` references

### Step 6: Test

- Run lib_cruncher locally
- Verify supplier search works through the UI
- Verify all four providers return results
- Verify variant selection and apply still work
- Verify the settings page can configure and test the connection

### Step 7: Deploy

- Add `SCM_URL` and `SCM_TOKEN` to lib_cruncher's Appliku env vars
- Push to staging/production
- Verify on deployed instance

## Deployed Configuration

On Appliku, lib_cruncher needs two new env vars:

```
SCM_URL=https://scm.wavenumber.net
SCM_TOKEN=<the service token>
```

No vendor credentials needed in lib_cruncher's deployment.

## Risks

- SCM service downtime blocks all supplier searches (acceptable — same as any
  API dependency)
- Network latency adds ~50-200ms overhead per search vs direct imports
  (negligible compared to provider response times of 300-3000ms)
- Local development requires either SCM_TOKEN for the remote service or running
  SCM locally

## bom_cruncher

bom_cruncher will follow the same pattern later. It references `JLCPCB Part #`
in exports and transforms. When ready, it would depend on `scm[client]` the same
way and use `SCMClient` for any supplier lookups it needs.
