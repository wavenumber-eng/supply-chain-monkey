# Supply Chain Monkey

```text
          ▓▓▓▓▓▓▓▓▓▓
        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    ▓▓▓▓░░░░░░▓▓░░░░░░▓▓▓▓
░░░░▓▓░░░░░░░░░░░░░░░░░░▓▓░░░░
░░░░▓▓░░██  ░░░░░░██  ░░▓▓░░░░
  ░░▓▓░░████░░░░░░████░░▓▓░░
    ▓▓░░░░░░░░░░░░░░░░░░▓▓
      ▓▓░░░░░░░░░░░░░░▓▓
        ▓▓▓▓░░░░░░▓▓▓▓
            ▓▓▓▓▓▓          ░░
          ▓▓▓▓▓▓▓▓▓▓      ▓▓
          ▓▓▓▓▓▓▓▓▓▓    ▓▓▓▓
        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
        ▓▓▓▓░░▓▓░░▓▓▓▓
```

Internal service for querying electronic component suppliers. It provides a
unified HTTP API that centralizes vendor credentials and provider routing.

Use the [documentation map](docs/README.md) for service operation, API
exploration, Python and Rust consumption, contract authoring, and release
material.

## Status

`2026.8.12` - explicit provider failure diagnostics in the API and status page,
including retryability and sanitized upstream context.

The PyPI distribution is `supply-chain-monkey`. The Python import package is
`scm`.

## Architecture

The repository contains four owned layers:

- `src/tsp/scm/v1`: authored TypeSpec HTTP and JSON structural authority.
- `scm.models`: supported Python contract surface backed by generated Pydantic
  models.
- `scm.client`: HTTP client library for consumers.
- `scm.server`: FastAPI server with provider adapters and the status page.

The Rust workspace contains generated contracts, a secure async client, and the
`scm` proof CLI. It consumes the service and has no Appliku deployment role.

## Providers

| Supplier | Backend | Credentials Required |
|---|---|---|
| JLCPCB | Public search, LCSC shared C-code resolution, plus hybrid detail | Optional; fallback works without credentials |
| LCSC | Primary and third-party website JSON APIs | None |
| Digikey | Official REST API v4 OAuth2 | Yes |
| Mouser | Official REST API v1 | Yes |

## API

All endpoints except health require a bearer token.

```text
GET  /v1/health
GET  /v1/providers/status
GET  /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR
GET  /v1/detail?supplier=jlcpcb&part=C2870085
GET  /v1/spn?supplier=jlcpcb&spn=C2870085
POST /v1/spn/batch
GET  /v1/search/stream?mpn=X&token=Y
```

The streaming endpoint pushes results per provider as they complete via
Server-Sent Events. It supports `max_results` and per-provider `timeout`, but is
a deprecated query-token compatibility surface. Never put a real service token
in its Swagger operation, logs, browser history, or a shared URL. New clients
use header-authenticated non-stream operations.

The root URL serves a status page with an interactive test panel.

Local and deployed servers expose:

- `/docs` and `/redoc` for FastAPI's runtime OpenAPI document;
- `/docs/typespec` for the canonical TypeSpec-generated OpenAPI document; and
- `/openapi.json` and `/openapi-typespec.json` for their OpenAPI 3.1 JSON.

See [API exploration](docs/guides/API_EXPLORATION.md) for PowerShell and POSIX
startup, authorization, safe smoke requests, and the distinction between the
two documents.

## Python client

Install the consumer client from PyPI:

```bash
python -m pip install "supply-chain-monkey[client]==2026.8.12"
```

```python
from scm.client import SCMClient
from scm.models import PARAMETER_FIELD_NAMES, SUPPLIERS, SupplierType

client = SCMClient(url="https://your-scm.example.com", token="...")

result = client.search("jlcpcb", "TPS543620RPYR")
all_results = client.search_all("TPS543620RPYR")
detail = client.detail("jlcpcb", "C2870085")
print(SUPPLIERS)
```

## Rust client

Before separately authorized crates.io publication, pin the reviewed immutable
repository revision:

```toml
[dependencies]
scm-client = { package = "supply-chain-monkey-client", git = "https://github.com/wavenumber-eng/supply-chain-monkey.git", rev = "e7bc0587e7a4b6435b993ce982505fb604861d20" }
tokio = { version = "1.53.1", features = ["macros", "rt-multi-thread"] }
```

The [Rust client guide](rust/src/scm-client/README.md) provides compiling
single-provider and concurrent-search examples, error classification, secure
builder options, and generated-contract access. The
[CLI guide](rust/src/scm-cli/README.md) covers interactive tables and JSON.

## Local Development

```bash
cp .env.template .env
# fill in SCM_SERVICE_TOKEN and any provider credentials

uv sync --group dev
PYTHONPATH=src/py uv run uvicorn scm.server.main:app --reload --env-file .env
```

Windows users can use the PowerShell commands in the
[API exploration guide](docs/guides/API_EXPLORATION.md#start-locally-on-powershell).

## Testing

```bash
uv run pytest -q
uv run rack run L99_signoff
npm run check:contracts
npm run check:python-generation
uv run python tests/scripts/scm_test_cli.py --token YOUR_TOKEN
uv run python tests/scripts/scm_test_cli.py --url https://your-scm.example.com --token YOUR_TOKEN
```

## Deployment

The included `appliku.yml` uses Appliku's managed `python-3.13-uv` build image.
Only pushing `production` triggers the configured Appliku deployment; `dev` is
integration-only.

```bash
git checkout dev
# merge through PRs; do not develop directly on production
```

`pyproject.toml` must keep `[tool.uv] package = false` and
`default-groups = []`. The Dockerfile is inactive unless `appliku.yml` changes
to `build_image: dockerfile`. See `CLAUDE.md` for deployment constraints.

`dev` is the integration branch. `main` is the public source branch.
`production` is the Wavenumber deployment branch and must be updated only by
protected PR/merge flow.

## Consumer Integration

Consumers should depend on the `supply-chain-monkey[client]` distribution and
import `scm`. Configure service URL and token outside source control.
