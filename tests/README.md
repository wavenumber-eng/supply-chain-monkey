# Supply Chain Monkey Tests

This suite currently provides one `L0_foundation` stratum for the migrated
supplier service package.

Rules:

- active coverage is package-local
- no shared external test-corpus dependency is required
- live supplier tests are opt-in and controlled by local `.env` plus
  `SUPPLY_CHAIN_ENABLE_LIVE_TESTS=1`
- `input/`, `reference_output/`, and `output/` remain the preferred case shape
  when broader fixture families appear later
- `output/` is transient

Quick start:

```powershell
cd C:\path\to\supply-chain-monkey
uv sync --group dev
$env:RACK_TESTS_DIR = (Resolve-Path tests)
uv run rack list
uv run rack run L0_foundation
```

## Live Provider Env

To enable live Digikey/Mouser coverage:

```powershell
Copy-Item .env.template .env
# fill credentials, then:
$env:SUPPLY_CHAIN_ENABLE_LIVE_TESTS = "1"
$env:RACK_TESTS_DIR = (Resolve-Path tests)
uv run rack run L0_foundation
```

Important notes:

- `supply-chain-monkey/.env` is intended to stay local and untracked.
- Digikey and Mouser are the primary live-provider checks.
- JLCPCB and LCSC are scraper-backed and can fail because the upstream site
  changed.
- To validate API-backed providers directly, run
  `tests/L0_foundation/test_supplier_interface.py`.
