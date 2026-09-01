"""Build and consume isolated Python and Rust release candidates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUST_ROOT = ROOT / "rust"
PUBLIC_CRATES = (
    "supply-chain-monkey-contracts",
    "supply-chain-monkey-client",
    "supply-chain-monkey-cli",
)
CATALOG_PATH = ROOT / "contracts/scm/v1/generated/contract_catalog.a0.json"
ROOTS_PATH = ROOT / "contracts/scm/v1/generated/contract_roots.a0.json"
OPENAPI_PATH = ROOT / "contracts/scm/v1/generated/openapi.json"
STAGING_ROOT = ROOT / "temp/artifact-candidates"


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
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
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed with exit code {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def schema_inventory() -> dict[str, str]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {
        Path(item["path"]).name: item["sha256"]
        for item in catalog["artifacts"]["schemas"]
    }


def verify_resource_inventory(
    names: set[str],
    read: Callable[[str], bytes],
    prefix: str,
) -> None:
    expected_schemas = schema_inventory()
    expected = {
        f"{prefix}contract_catalog.a0.json": sha256(CATALOG_PATH),
        f"{prefix}contract_roots.a0.json": sha256(ROOTS_PATH),
        f"{prefix}openapi.json": sha256(OPENAPI_PATH),
        **{
            f"{prefix}schema/{name}": digest
            for name, digest in expected_schemas.items()
        },
    }
    missing = set(expected) - names
    if missing:
        raise RuntimeError(f"artifact is missing generated resources: {sorted(missing)}")
    actual_schemas = {
        name for name in names if name.startswith(f"{prefix}schema/") and name.endswith(".json")
    }
    expected_schema_paths = {name for name in expected if "/schema/" in name}
    if actual_schemas != expected_schema_paths:
        raise RuntimeError("artifact schema resource inventory is not catalog-exact")
    for name, digest in expected.items():
        content = read(name)
        if sha256_bytes(content) != digest:
            raise RuntimeError(f"artifact resource digest mismatch: {name}")


def isolated_python_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def python_executable(venv: Path) -> Path:
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return venv / relative


def build_python_candidates(root: Path) -> list[Path]:
    wheelhouse = root / "python"
    run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--outdir",
            str(wheelhouse),
        ]
    )
    artifacts = sorted(path for path in wheelhouse.iterdir() if path.is_file())
    run(["uv", "run", "twine", "check", *[str(path) for path in artifacts]])
    wheel = next(path for path in artifacts if path.suffix == ".whl")
    sdist = next(path for path in artifacts if path.name.endswith(".tar.gz"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        verify_resource_inventory(
            names,
            archive.read,
            "scm/generated/v1/resources/",
        )
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        if any("/target/" in f"/{member.name}/" for member in members):
            raise RuntimeError("Python sdist contains a transient Cargo target tree")
        roots = {Path(member.name).parts[0] for member in members}
        if len(roots) != 1:
            raise RuntimeError("Python sdist has an unexpected root inventory")
        prefix = f"{roots.pop()}/scm/generated/v1/resources/"
        files = {member.name: member for member in members if member.isfile()}

        def read_sdist(name: str) -> bytes:
            stream = archive.extractfile(files[name])
            if stream is None:
                raise RuntimeError(f"could not read sdist resource: {name}")
            return stream.read()

        verify_resource_inventory(set(files), read_sdist, prefix)

    venv = root / "python-venv"
    run(["uv", "venv", str(venv), "--python", "3.13"])
    executable = python_executable(venv)
    run(["uv", "pip", "install", "--python", str(executable), str(wheel)])
    proof = """
import sys
from importlib import resources
from pathlib import Path
import scm
from scm.client import SCMClient
from scm.models import HealthResponse, SearchEnvelope, SpnBatchRequest

root = resources.files("scm.generated.v1.resources")
prefix = Path(sys.prefix).resolve()
assert scm.__file__ is not None
assert Path(scm.__file__).resolve().is_relative_to(prefix)
assert Path(str(root)).resolve().is_relative_to(prefix)
assert root.joinpath("contract_catalog.a0.json").is_file()
assert root.joinpath("openapi.json").is_file()
assert root.joinpath("schema/HealthResponse.json").is_file()
assert SpnBatchRequest(supplier="LCSC", spns=["C123"]).include_raw is False
assert HealthResponse and SearchEnvelope and SCMClient
"""
    environment = isolated_python_environment()
    result = subprocess.run(
        [str(executable), "-I", "-c", proof],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"isolated wheel proof failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return artifacts


def extract_crate(archive: Path, root: Path) -> Path:
    with tarfile.open(archive, "r:gz") as crate:
        crate.extractall(root, filter="data")
        top_levels = {Path(member.name).parts[0] for member in crate.getmembers()}
    if len(top_levels) != 1:
        raise RuntimeError(f"unexpected crate archive roots: {sorted(top_levels)}")
    return root / top_levels.pop()


def build_rust_candidates(root: Path) -> list[Path]:
    cargo_target = root / "cargo-target"
    run(
        [
            "cargo",
            "package",
            "-p",
            "supply-chain-monkey-contracts",
            "-p",
            "supply-chain-monkey-client",
            "-p",
            "supply-chain-monkey-cli",
            "--locked",
        ],
        cwd=RUST_ROOT,
        extra_env={"CARGO_TARGET_DIR": str(cargo_target)},
    )
    package_root = cargo_target / "package"
    archives = [package_root / f"{name}-0.1.0.crate" for name in PUBLIC_CRATES]
    missing = [str(path) for path in archives if not path.is_file()]
    if missing:
        raise RuntimeError(f"Cargo package did not emit candidates: {missing}")

    extracted = root / "rust-packages"
    extracted.mkdir()
    contracts = extract_crate(archives[0], extracted)
    client = extract_crate(archives[1], extracted)
    cli = extract_crate(archives[2], extracted)
    for package in (contracts, client, cli):
        if not package.joinpath("LICENSE").is_file():
            raise RuntimeError(f"{package.name} package is missing LICENSE")
    expected_schemas = schema_inventory()
    actual_schemas = {
        path.name: sha256(path) for path in contracts.joinpath("schema").glob("*.json")
    }
    if actual_schemas != expected_schemas:
        raise RuntimeError("scm-contracts schema inventory or content is not catalog-exact")

    consumer = root / "alexandria-scm-consumer"
    shutil.copytree(
        ROOT / "tests/consumers/alexandria-scm",
        consumer,
        ignore=shutil.ignore_patterns("Cargo.lock", "target"),
    )
    manifest = f"""
[patch.crates-io]
supply-chain-monkey-contracts = {{ path = {json.dumps(contracts.as_posix())} }}
supply-chain-monkey-client = {{ path = {json.dumps(client.as_posix())} }}
"""
    with consumer.joinpath("Cargo.toml").open("a", encoding="utf-8") as stream:
        stream.write(manifest)
    consumer_env = {
        "CARGO_TARGET_DIR": str(root / "consumer-target"),
        "RUSTUP_TOOLCHAIN": "1.96.1",
    }
    run(["cargo", "generate-lockfile"], cwd=consumer, extra_env=consumer_env)
    run(
        ["cargo", "clippy", "--locked", "--all-targets", "--", "-D", "warnings"],
        cwd=consumer,
        extra_env=consumer_env,
    )
    run(
        ["cargo", "test", "--locked", "--all-targets"],
        cwd=consumer,
        extra_env=consumer_env,
    )
    return archives


def source_state() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    return {"commit": commit, "dirty": bool(status)}


def retain_candidates(artifacts: list[Path]) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for artifact in artifacts:
        digest = sha256(artifact)
        destination = STAGING_ROOT / "sha256" / digest / artifact.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
        entries.append(
            {
                "name": artifact.name,
                "path": destination.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "size": artifact.stat().st_size,
            }
        )
    report: dict[str, object] = {
        "format": "scm.artifact-candidates.a0",
        "source": source_state(),
        "artifacts": entries,
    }
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    pending = STAGING_ROOT / "latest.json.pending"
    manifest = STAGING_ROOT / "latest.json"
    pending.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(manifest)
    report["manifest"] = manifest.relative_to(ROOT).as_posix()
    return report


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="scm-artifact-proof-") as temporary:
        root = Path(temporary)
        artifacts = [*build_python_candidates(root), *build_rust_candidates(root)]
        report = retain_candidates(artifacts)
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
