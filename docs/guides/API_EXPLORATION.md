# Explore the SCM API

The FastAPI test server exposes two complementary OpenAPI documents:

- `/openapi.json` is FastAPI's runtime projection and drives `/docs` and
  `/redoc`.
- `/openapi-typespec.json` is the packaged TypeSpec-generated structural
  authority and drives `/docs/typespec`.

Tests require both documents to agree on paths, version, operation summaries,
descriptions, deprecation, response roots, and security metadata. The schemas
need not be byte-identical because FastAPI names its generated Pydantic
components differently.

## Start locally on PowerShell

From the repository root:

```powershell
Copy-Item .env.template .env
# Put a local-only SCM_SERVICE_TOKEN and any optional provider credentials in .env.

$env:PYTHONPATH = (Resolve-Path .\src\py).Path
uv sync --group dev
uv run uvicorn scm.server.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
```

To avoid an environment file, set values only in the current process:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src\py).Path
$env:SCM_SERVICE_TOKEN = "local-test-token"
uv run uvicorn scm.server.main:app --host 127.0.0.1 --port 8000 --reload
```

## Start locally on POSIX shells

```bash
cp .env.template .env
# Put a local-only SCM_SERVICE_TOKEN and any optional provider credentials in .env.

uv sync --group dev
PYTHONPATH=src/py uv run uvicorn scm.server.main:app \
  --host 127.0.0.1 --port 8000 --reload --env-file .env
```

## Explorer URLs

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/docs` | Interactive runtime Swagger UI |
| `http://127.0.0.1:8000/redoc` | Read-only runtime ReDoc |
| `http://127.0.0.1:8000/openapi.json` | Runtime OpenAPI 3.1 JSON |
| `http://127.0.0.1:8000/docs/typespec` | Interactive canonical TypeSpec Swagger UI |
| `http://127.0.0.1:8000/openapi-typespec.json` | Canonical TypeSpec OpenAPI 3.1 JSON |
| `http://127.0.0.1:8000/v1/` | Human-facing SCM status page |

The Swagger HTML loads its normal UI assets in the browser, but both SCM
specifications remain served by the local SCM process. Do not upload an
internal specification or a token to a third-party OpenAPI editor.

## Authenticate safely

`GET /v1/health` and the HTML status page are public. In either Swagger view,
select **Authorize**, choose `BearerAuth`, and enter only the raw value of the
local `SCM_SERVICE_TOKEN`; Swagger adds the `Bearer` prefix.

For a non-provider smoke request in PowerShell:

```powershell
$headers = @{ Authorization = "Bearer $env:SCM_SERVICE_TOKEN" }
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/search?supplier=unknown&mpn=RT685" `
  -Headers $headers
```

An unknown supplier returns a typed `provider_error` envelope without calling a
live supplier. Real provider searches additionally require their documented
process-environment credentials.

## Legacy stream warning

`GET /v1/search/stream` is a deprecated v1 compatibility endpoint whose token
is a query parameter. Never place a real service token in that query, either
Swagger operation, logs, browser history, or a shared URL. The Rust client and
CLI intentionally omit it. New consumers use header-authenticated non-stream
operations.

## Validate generated documentation

These commands compile TypeSpec, regenerate into a temporary directory, compare
checked-in artifacts, and enforce documentation coverage:

```powershell
npm run check:typespec
npm run check:contracts
npm run check:python-generation
```

`npm run check:documentation` is the focused semantic-documentation check. It
uses the TypeSpec compiler API to require documentation for every authored
declaration, member, operation, and parameter, then checks generated OpenAPI
summaries, descriptions, version, and legacy-token warnings.
