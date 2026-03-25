from __future__ import annotations

import os
from pathlib import Path


def _package_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_env_paths(start_dir: Path | None = None) -> list[Path]:
    start = (start_dir or Path.cwd()).resolve()
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if path not in seen:
            candidates.append(path)
            seen.add(path)

    for base in [start, *start.parents]:
        add(base / ".env")
        add(base / ".env.local")

    member_root = _package_root()
    workspace_root = member_root.parent
    home = Path.home()

    for base in [member_root, workspace_root, home]:
        add(base / ".env")
        add(base / ".env.local")

    return candidates


def get_env_file_path(start_dir: Path | None = None) -> Path | None:
    for candidate in _candidate_env_paths(start_dir=start_dir):
        if candidate.exists():
            return candidate
    return None


def load_env_file(
    path: Path | None = None,
    *,
    start_dir: Path | None = None,
    set_environ: bool = False,
    override: bool = False,
) -> dict[str, str]:
    env_path = path or get_env_file_path(start_dir=start_dir)
    if env_path is None or not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value

    if set_environ:
        for key, value in values.items():
            if override or key not in os.environ:
                os.environ[key] = value

    return values


def ensure_env_loaded(*, override: bool = False, start_dir: Path | None = None) -> dict[str, str]:
    return load_env_file(start_dir=start_dir, set_environ=True, override=override)
