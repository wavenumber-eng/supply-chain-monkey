# Contributing

Use the production branch as the deployed baseline and keep changes narrow.

```powershell
uv sync --group dev
uv run rack run L99_signoff
```

Do not commit secrets, generated build output, local virtual environments, or
live supplier response dumps. Live provider checks require explicit credentials
and `SUPPLY_CHAIN_ENABLE_LIVE_TESTS=1`.
