from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "temp",
}
TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".ps1",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_NAMES = {"pyproject.toml"}


def pruning_config() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    return pyproject["tool"]["wn_dev_std"]["compatibility_pruning"]


def test_configured_compatibility_pruning_patterns_are_absent() -> None:
    config = pruning_config()
    patterns = [re.compile(pattern) for pattern in config["forbidden_patterns"]]
    excluded_parts = DEFAULT_EXCLUDED_PARTS | set(config.get("excluded_parts", []))
    scan_root = (ROOT / config.get("root", ".")).resolve()

    violations: list[str] = []
    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(scan_root)
        if set(relative.parts) & excluded_parts:
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitattributes"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for pattern in patterns:
                if pattern.search(line):
                    violations.append(f"{relative.as_posix()}:{line_number}: {pattern.pattern}")

    assert not violations, "forbidden compatibility references found:\n" + "\n".join(
        violations[:25]
    )
