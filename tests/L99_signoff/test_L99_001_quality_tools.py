from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_checked(command: list[str], *, cwd: Path = ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    assert result.returncode == 0, (
        f"{' '.join(command)} failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_ruff_passes() -> None:
    run_checked(["ruff", "check", "."])


def test_pyright_passes() -> None:
    run_checked(["pyright"])


def test_uv_lock_is_current() -> None:
    run_checked(["uv", "lock", "--check"])


def test_wheel_builds_and_checks(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    run_checked([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(wheelhouse)])
    wheels = sorted(wheelhouse.glob("*.whl"))
    sdists = sorted(wheelhouse.glob("*.tar.gz"))
    assert wheels, "wheel build did not produce a wheel"
    assert sdists, "sdist build did not produce a source distribution"
    run_checked(["twine", "check", *[str(path) for path in [*sdists, *wheels]]])
