from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUST_ROOT = ROOT / "rust"


def run_checked(
    command: list[str],
    *,
    cwd: Path = RUST_ROOT,
    extra_env: dict[str, str] | None = None,
) -> None:
    environment = os.environ.copy()
    environment.update(extra_env or {})
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{' '.join(command)} failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_pinned_rust_dev_std_policy_passes() -> None:
    run_checked(
        [
            "uvx",
            "--from",
            "wn-dev-std==2026.8.12",
            "dev-std",
            "audit",
            "rust",
            "--scope",
            "repo",
            "--scope",
            "language",
        ],
        cwd=ROOT,
    )


@pytest.mark.parametrize(
    "command",
    [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "run", "-p", "scm-codegen", "--locked", "--", "--check"],
        ["cargo", "check", "--workspace", "--all-targets", "--all-features", "--locked"],
        [
            "cargo",
            "clippy",
            "--workspace",
            "--all-targets",
            "--all-features",
            "--locked",
            "--",
            "-D",
            "warnings",
        ],
        ["cargo", "test", "--workspace", "--all-features", "--locked"],
        ["cargo", "test", "--workspace", "--doc", "--locked"],
        ["cargo", "doc", "--workspace", "--no-deps", "--locked"],
    ],
    ids=["format", "generation", "check", "clippy", "test", "doctest", "rustdoc"],
)
def test_locked_rust_workspace_gate(command: list[str]) -> None:
    extra_env = {"RUSTDOCFLAGS": "-D warnings"} if command[1] == "doc" else None
    run_checked(command, extra_env=extra_env)
