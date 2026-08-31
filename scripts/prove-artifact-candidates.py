"""Build and consume isolated Python and Rust release candidates."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUST_ROOT = ROOT / "rust"
PUBLIC_CRATES = ("scm-contracts", "scm-client", "scm-cli")


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
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
    required = {
        "scm/generated/v1/resources/contract_catalog.a0.json",
        "scm/generated/v1/resources/contract_roots.a0.json",
        "scm/generated/v1/resources/schema/HealthResponse.json",
    }
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise RuntimeError(f"wheel is missing generated resources: {sorted(missing)}")
    with tarfile.open(sdist, "r:gz") as archive:
        if any("/rust/target/" in member.name for member in archive.getmembers()):
            raise RuntimeError("Python sdist contains the transient Rust target tree")

    venv = root / "python-venv"
    run(["uv", "venv", str(venv), "--python", "3.13"])
    executable = python_executable(venv)
    run(["uv", "pip", "install", "--python", str(executable), str(wheel)])
    proof = """
from importlib import resources
from scm.client import SCMClient
from scm.models import HealthResponse, SearchEnvelope, SpnBatchRequest

root = resources.files("scm.generated.v1.resources")
assert root.joinpath("contract_catalog.a0.json").is_file()
assert root.joinpath("schema/HealthResponse.json").is_file()
assert SpnBatchRequest(supplier="LCSC", spns=["C123"]).include_raw is False
assert HealthResponse and SearchEnvelope and SCMClient
"""
    run([str(executable), "-c", proof], cwd=root)
    return artifacts


def extract_crate(archive: Path, root: Path) -> Path:
    with tarfile.open(archive, "r:gz") as crate:
        crate.extractall(root, filter="data")
        top_levels = {Path(member.name).parts[0] for member in crate.getmembers()}
    if len(top_levels) != 1:
        raise RuntimeError(f"unexpected crate archive roots: {sorted(top_levels)}")
    return root / top_levels.pop()


def build_rust_candidates(root: Path) -> list[Path]:
    run(
        [
            "cargo",
            "package",
            "-p",
            "scm-contracts",
            "-p",
            "scm-client",
            "-p",
            "scm-cli",
            "--locked",
        ],
        cwd=RUST_ROOT,
    )
    package_root = RUST_ROOT / "target" / "package"
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
    if len(list(contracts.joinpath("schema").glob("*.json"))) != 35:
        raise RuntimeError("scm-contracts package does not contain all 35 schema resources")

    consumer = root / "rust-consumer"
    consumer.joinpath("src").mkdir(parents=True)
    manifest = f"""[package]
name = "scm-packaged-candidate-consumer"
version = "0.0.0"
edition = "2024"

[dependencies]
scm-client = {{ path = {json.dumps(client.as_posix())}, version = "=0.1.0" }}

[patch.crates-io]
scm-contracts = {{ path = {json.dumps(contracts.as_posix())} }}
"""
    consumer.joinpath("Cargo.toml").write_text(manifest, encoding="utf-8")
    consumer.joinpath("src/main.rs").write_text(
        """use scm_client::ScmClient;

fn main() {
    let client = ScmClient::builder("https://scm.example.invalid")
        .expect("packaged client builder")
        .build()
        .expect("packaged client");
    let _ = format!("{client:?}");
}
""",
        encoding="utf-8",
    )
    run(["cargo", "generate-lockfile"], cwd=consumer)
    run(["cargo", "check", "--locked"], cwd=consumer)
    return archives


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="scm-artifact-proof-") as temporary:
        root = Path(temporary)
        artifacts = [*build_python_candidates(root), *build_rust_candidates(root)]
        report = {
            "artifacts": [
                {
                    "name": path.name,
                    "sha256": sha256(path),
                    "size": path.stat().st_size,
                }
                for path in artifacts
            ]
        }
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
