# Supply Chain Monkey Agent Guide

## Rules

- Treat `dev` as the integration branch and `production` as the deployed
  release branch.
- Keep Appliku deployment changes small and verify the full signoff before
  opening a PR into `production`.
- Do not hardcode company deployment URLs or credentials in source.
- Keep `[tool.uv] package = false`; Appliku imports the app with `PYTHONPATH`.
- Keep `appliku.yml` on the managed `python-3.13-uv` image unless a full
  Dockerfile deploy cycle is being tested.
- If `build_image: dockerfile` is introduced, update the Dockerfile, docs, and
  L99 Appliku tests in the same change.
- Provider credentials come from process environment through
  `scm.server.settings`. Do not reintroduce provider-level `.env` loaders.
- Do not add alternate import-path compatibility shims.

## Commands

```powershell
uv sync --group dev
uv run pytest -q
uv run rack run L99_signoff
uv run python -m build --sdist --wheel --outdir temp\dist
uv run twine check temp\dist\*
```

Live supplier tests are opt-in:

```powershell
$env:SUPPLY_CHAIN_ENABLE_LIVE_TESTS = "1"
uv run pytest tests\L0_foundation\test_supplier_interface.py -q
```
