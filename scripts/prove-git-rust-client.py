"""Prove the documented immutable Git dependency from an isolated project."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


GIT_URL = "https://github.com/wavenumber-eng/supply-chain-monkey.git"
GIT_REVISION = "ce2c126066fbda260947fdac3bee8db40ad4e61b"
CARGO_TOML = f"""\
[package]
name = "scm-git-consumer-proof"
version = "0.0.0"
edition = "2024"
publish = false

[dependencies]
scm-client = {{ package = "supply-chain-monkey-client", git = "{GIT_URL}", rev = "{GIT_REVISION}" }}
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
    with tempfile.TemporaryDirectory(prefix="scm-git-consumer-") as temporary:
        project = Path(temporary)
        source_root = project / "src"
        source_root.mkdir()
        (project / "Cargo.toml").write_text(CARGO_TOML, encoding="utf-8")
        (source_root / "lib.rs").write_text(SOURCE, encoding="utf-8")
        environment = os.environ.copy()
        environment["CARGO_TARGET_DIR"] = str(project / "target")
        environment["RUSTFLAGS"] = "-D warnings"
        run(["cargo", "+1.96.1", "generate-lockfile"], project, environment)
        lock = (project / "Cargo.lock").read_text(encoding="utf-8")
        expected = f"git+{GIT_URL}?rev={GIT_REVISION}#{GIT_REVISION}"
        if expected not in lock:
            raise RuntimeError("Cargo.lock did not resolve the documented immutable revision")
        run(["cargo", "+1.96.1", "test", "--locked"], project, environment)
    print(f"Isolated Rust Git consumer passed at {GIT_REVISION}.")


def run(command: list[str], cwd: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(command, cwd=cwd, env=environment, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {command}")


if __name__ == "__main__":
    main()
