from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def load_appliku() -> dict:
    return yaml.safe_load((ROOT / "appliku.yml").read_text(encoding="utf-8"))


def run_checked(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0, (
        f"{' '.join(command)} failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def test_appliku_managed_build_contract() -> None:
    pyproject = load_pyproject()
    appliku = load_appliku()

    assert pyproject["tool"]["uv"]["package"] is False
    assert pyproject["tool"]["uv"]["default-groups"] == []
    assert pyproject["project"]["readme"] == "README.md"

    dependencies = "\n".join(pyproject["project"]["dependencies"])
    for dependency in ("pydantic", "requests", "fastapi", "uvicorn"):
        assert dependency in dependencies

    build_settings = appliku["build_settings"]
    assert build_settings["build_image"] == "python-3.13-uv"
    assert build_settings["container_port"] == 8000

    command = appliku["services"]["web"]["command"]
    assert command.startswith("bash -c ")
    assert "PYTHONPATH=/code/src/py" in command
    assert "uvicorn scm.server.main:app" in command
    assert "--host 0.0.0.0" in command
    assert "--port 8000" in command
    assert "--no-access-log" in command
    assert "--reload" not in command


def test_legacy_query_token_cannot_reach_production_access_logs() -> None:
    marker = "SCM_ACCESS_LOG_SECRET_MARKER"
    command = load_appliku()["services"]["web"]["command"]

    assert marker not in command
    assert "--no-access-log" in command


def test_dockerfile_is_inactive_unless_appliku_selects_it() -> None:
    appliku = load_appliku()
    build_image = appliku["build_settings"]["build_image"]
    if build_image == "dockerfile":
        dockerfile_path = appliku["build_settings"].get("dockerfile_path", "Dockerfile")
        assert (ROOT / dockerfile_path).exists()
    else:
        assert build_image != "dockerfile"


def test_appliku_manifest_only_dependency_sync(tmp_path: Path) -> None:
    build_dir = tmp_path / "appliku-manifest"
    build_dir.mkdir()
    shutil.copy2(ROOT / "pyproject.toml", build_dir / "pyproject.toml")
    shutil.copy2(ROOT / "uv.lock", build_dir / "uv.lock")

    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / "venv")
    run_checked(["uv", "sync", "--frozen"], cwd=build_dir, env=env)

    run_checked(
        [
            str(venv_python(tmp_path / "venv")),
            "-c",
            "import fastapi, requests, uvicorn; print(fastapi.__name__, requests.__name__, uvicorn.__name__)",
        ],
        cwd=build_dir,
        env=env,
    )


def test_appliku_runtime_imports_with_pythonpath() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src" / "py")
    run_checked(
        [
            sys.executable,
            "-c",
            "from scm.server.main import app; assert app.title == 'supply-chain-monkey'",
        ],
        env=env,
    )
