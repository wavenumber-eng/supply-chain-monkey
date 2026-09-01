"""Prove the documented immutable Git dependency from an isolated project."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTED_DEPENDENCIES = (
    ROOT / "README.md",
    ROOT / "rust/README.md",
    ROOT / "rust/src/scm-client/README.md",
    ROOT / "tests/consumers/alexandria-scm/README.md",
)
DEPENDENCY = re.compile(
    r'scm-client = \{ package = "supply-chain-monkey-client", '
    r'git = "([^"]+)", rev = "([0-9a-f]{40})" \}'
)
SCM_PACKAGES = {"supply-chain-monkey-client", "supply-chain-monkey-contracts"}


def cargo_toml(git_url: str, git_revision: str) -> str:
    return f"""\
[package]
name = "scm-git-consumer-proof"
version = "0.0.0"
edition = "2024"
publish = false

[dependencies]
scm-client = {{ package = "supply-chain-monkey-client", git = "{git_url}", rev = "{git_revision}" }}
"""


SOURCE = """\
#[cfg(test)]
mod tests {
    use scm_client::{ProviderOutcome, ScmClient};

    fn compile_supported_operations(client: &ScmClient) {
        let search = client.search("lcsc", "RT685");
        let concurrent = client.search_all("RT685", ["jlcpcb", "lcsc"]);
        let _: Option<ProviderOutcome<scm_client::contracts::SearchEnvelope>> = None;
        drop((search, concurrent));
    }

    #[test]
    fn constructs_a_loopback_client_without_exposing_the_token() {
        let client = ScmClient::new("http://127.0.0.1:8000", "isolated-proof-token")
            .expect("loopback development URL should be accepted");
        let debug = format!("{client:?}");
        assert!(debug.contains("has_bearer_token: true"));
        assert!(!debug.contains("isolated-proof-token"));
        compile_supported_operations(&client);
    }
}
"""


def main() -> None:
    git_url, git_revision = documented_dependency()
    with tempfile.TemporaryDirectory(prefix="scm-git-consumer-") as temporary:
        project = Path(temporary)
        cargo_home = project / "cargo-home"
        cargo_home.mkdir()
        source_root = project / "src"
        source_root.mkdir()
        (project / "Cargo.toml").write_text(
            cargo_toml(git_url, git_revision), encoding="utf-8"
        )
        (source_root / "lib.rs").write_text(SOURCE, encoding="utf-8")
        environment = clean_environment()
        environment["CARGO_HOME"] = str(cargo_home)
        environment["CARGO_TARGET_DIR"] = str(project / "target")
        environment["RUSTFLAGS"] = "-D warnings"
        run(["cargo", "+1.96.1", "generate-lockfile"], project, environment)
        expected = f"git+{git_url}?rev={git_revision}#{git_revision}"
        verify_lock(project / "Cargo.lock", expected)
        metadata = run(
            ["cargo", "+1.96.1", "metadata", "--locked", "--format-version=1"],
            project,
            environment,
            capture=True,
        )
        verify_metadata(json.loads(metadata), expected, cargo_home)
        run(["cargo", "+1.96.1", "test", "--locked"], project, environment)
    print(f"Isolated Rust Git consumer passed at {git_revision}.")


def documented_dependency() -> tuple[str, str]:
    dependencies = set()
    for document in DOCUMENTED_DEPENDENCIES:
        match = DEPENDENCY.search(document.read_text(encoding="utf-8"))
        if match is None:
            raise RuntimeError(f"documented Git dependency is missing from {document}")
        dependencies.add(match.groups())
    if len(dependencies) != 1:
        raise RuntimeError("documented Rust Git dependencies do not agree")
    return dependencies.pop()


def clean_environment() -> dict[str, str]:
    blocked = {"RUSTC", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTFLAGS"}
    return {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("CARGO_") and name.upper() not in blocked
    }


def verify_lock(path: Path, expected_source: str) -> None:
    lock = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in lock["package"] if item["name"] in SCM_PACKAGES}
    if set(packages) != SCM_PACKAGES:
        raise RuntimeError("Cargo.lock does not contain both SCM Rust packages")
    for name, package in packages.items():
        if package.get("source") != expected_source:
            raise RuntimeError(f"Cargo.lock resolved {name} from an unexpected source")


def verify_metadata(metadata: dict, expected_source: str, cargo_home: Path) -> None:
    packages = {
        item["name"]: item for item in metadata["packages"] if item["name"] in SCM_PACKAGES
    }
    if set(packages) != SCM_PACKAGES:
        raise RuntimeError("Cargo metadata does not contain both SCM Rust packages")
    for name, package in packages.items():
        if package.get("source") != expected_source:
            raise RuntimeError(f"Cargo metadata resolved {name} from an unexpected source")
        manifest = Path(package["manifest_path"]).resolve()
        if not manifest.is_relative_to(cargo_home.resolve()) or manifest.is_relative_to(ROOT):
            raise RuntimeError(f"Cargo metadata resolved {name} outside the isolated Cargo home")


def run(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    *,
    capture: bool = False,
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=capture,
        text=capture,
    )
    if completed.returncode != 0:
        if capture:
            print(completed.stdout)
            print(completed.stderr)
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {command}")
    return completed.stdout if capture else ""


if __name__ == "__main__":
    main()
