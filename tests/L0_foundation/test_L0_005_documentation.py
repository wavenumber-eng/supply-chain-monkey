"""Fast documentation navigation and immutable-consumer regression checks."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs/README.md",
    ROOT / "docs/contracts/README.md",
    ROOT / "docs/guides/API_EXPLORATION.md",
    ROOT / "docs/plans/README.md",
    ROOT / "rust/README.md",
    ROOT / "rust/src/scm-client/README.md",
    ROOT / "rust/src/scm-contracts/README.md",
    ROOT / "rust/src/scm-cli/README.md",
    ROOT / "tests/consumers/alexandria-scm/README.md",
)
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
GIT_REVISION = re.compile(
    r'git = "https://github\.com/wavenumber-eng/supply-chain-monkey\.git", '
    r'rev = "([0-9a-f]{40})"'
)


def test_documentation_map_and_touched_readmes_have_valid_local_links():
    failures: list[str] = []
    for document in DOCUMENTS:
        assert document.is_file(), document.relative_to(ROOT).as_posix()
        source = document.read_text(encoding="utf-8")
        for target in LINK.findall(source):
            if target.startswith(("#", "https://", "http://", "mailto:")):
                continue
            path_text = target.split("#", 1)[0].strip()
            if not path_text:
                continue
            resolved = (document.parent / path_text).resolve()
            if not resolved.exists():
                failures.append(
                    f"{document.relative_to(ROOT).as_posix()} -> {target}"
                )
    assert failures == []


def test_rust_consumer_documentation_pins_one_immutable_revision():
    revisions: set[str] = set()
    for relative in (
        "README.md",
        "rust/README.md",
        "rust/src/scm-client/README.md",
        "tests/consumers/alexandria-scm/README.md",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        match = GIT_REVISION.search(source)
        assert match, relative
        revisions.add(match.group(1))
    assert revisions == {"ce2c126066fbda260947fdac3bee8db40ad4e61b"}


def test_api_exploration_guide_covers_both_documents_and_token_safety():
    guide = (ROOT / "docs/guides/API_EXPLORATION.md").read_text(encoding="utf-8")
    for required in (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/typespec",
        "/openapi-typespec.json",
        "PowerShell",
        "POSIX",
        "Never place a real service token",
        "Do not upload",
    ):
        assert required in guide
