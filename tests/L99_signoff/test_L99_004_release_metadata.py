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
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/py/scm"
    ]


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
    assert "password" not in steps_text
    assert "TWINE_PASSWORD" not in steps_text
