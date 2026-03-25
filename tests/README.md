# Supply Chain Monkey Tests

This private suite currently provides one `L0_foundation` stratum for the migrated `supply_chain_monkey` package.

Rules:
- active coverage is package-local
- no shared `WN_TEST_CORPUS` dependency is required
- live supplier tests are opt-in and controlled by:
  - local `.env`
  - `SUPPLY_CHAIN_ENABLE_LIVE_TESTS=1`
- `input/`, `reference_output/`, and `output/` remain the preferred case shape when broader fixture families appear later
- `output/` is transient

Quick start:

```powershell
cd C:\eli\toolz\supply_chain_monkey
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

- `supply_chain_monkey/.env` is intended to stay local and untracked.
- Digikey and Mouser are the primary live-provider checks.
- JLCPCB and LCSC are scraper-backed and can fail because the upstream site changed.
- If you only want to validate the API-backed providers directly, run the specific tests in:
  - [test_supplier_interface.py](C:/eli/toolz/supply_chain_monkey/tests/L0_foundation/test_supplier_interface.py)
