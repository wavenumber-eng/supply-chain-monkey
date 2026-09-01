from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DATE_VERSION = re.compile(r"^(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})$")


def load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_package_identity_uses_public_distribution_and_scm_import() -> None:
    pyproject = load_pyproject()

    assert pyproject["project"]["name"] == "supply-chain-monkey"
    targets = pyproject["tool"]["hatch"]["build"]["targets"]
    assert targets["wheel"]["packages"] == ["src/py/scm"]
    assert targets["wheel"]["core-metadata-version"] == "2.4"
    assert targets["sdist"]["core-metadata-version"] == "2.4"


def test_version_is_date_based_and_matches_import_version() -> None:
    pyproject = load_pyproject()
    version = pyproject["project"]["version"]
    match = DATE_VERSION.fullmatch(version)

    assert match is not None
    month = int(match.group("month"))
    day = int(match.group("day"))
    assert 1 <= month <= 12
    assert 1 <= day <= 31

    init_text = (ROOT / "src" / "py" / "scm" / "__init__.py").read_text(encoding="utf-8")
    assert f'__version__ = "{version}"' in init_text


def test_release_note_matches_date_version() -> None:
    version = load_pyproject()["project"]["version"]
    year, month, day = (int(part) for part in version.split("."))
    release_note = ROOT / "docs" / "releases" / f"{year:04d}-{month:02d}-{day:02d}.md"

    assert release_note.exists()
    text = release_note.read_text(encoding="utf-8")
    assert f"`{version}`" in text
    assert "supply-chain-monkey" in text
    assert "scm" in text


def test_pypi_trusted_publisher_workflow_is_configured() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "release.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    publish_job = workflow["jobs"]["publish"]
    permissions = publish_job.get("permissions", workflow.get("permissions", {}))

    assert publish_job["environment"] == "pypi"
    assert permissions["id-token"] == "write"

    steps_text = "\n".join(str(step) for step in publish_job["steps"])
    assert "pypa/gh-action-pypi-publish@release/v1" in steps_text
    assert "npm install --global npm@11.16.0" in steps_text
    assert "cargo +1.96.1 install --locked cargo-deny --version 0.20.2" in steps_text
    for command in (
        "npm ci",
        "npm run check:typespec",
        "npm run check:contracts",
        "npm run check:vectors",
        "npm run check:python-generation",
    ):
        assert command in steps_text
    assert "password" not in steps_text
    assert "TWINE_PASSWORD" not in steps_text


def test_ci_checks_pinned_contract_and_cross_platform_rust_gates() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    signoff_steps = "\n".join(str(step) for step in workflow["jobs"]["signoff"]["steps"])
    assert "actions/setup-node@v6" in signoff_steps
    assert "node-version-file" in signoff_steps
    assert "npm install --global npm@11.16.0" in signoff_steps
    for command in (
        "npm ci",
        "npm run check:typespec",
        "npm run check:contracts",
        "npm run check:vectors",
        "npm run check:python-generation",
        "uv run rack run L99_signoff",
    ):
        assert command in signoff_steps

    rust_job = workflow["jobs"]["rust-signoff"]
    assert rust_job["strategy"]["matrix"]["os"] == [
        "macos-latest",
        "windows-latest",
    ]
    rust_steps = "\n".join(str(step) for step in rust_job["steps"])
    assert "rustup toolchain install 1.96.1" in rust_steps
    assert "cargo test --workspace --all-features --locked" in rust_steps

    linux_steps = "\n".join(str(step) for step in workflow["jobs"]["signoff"]["steps"])
    assert "cargo +1.96.1 install --locked cargo-deny --version 0.20.2" in linux_steps
