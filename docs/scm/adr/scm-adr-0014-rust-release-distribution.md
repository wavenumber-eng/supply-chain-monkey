# SCM ADR 0014: Rust release identities and distribution channels

## Status

Accepted on 2026-08-31. This decision defines channels; it does not authorize a
publication, GitHub Release, package-manager submission, or production deploy.

## Context

Supply Chain Monkey now has generated Rust contracts, an async client, and the
`scm` proof CLI. Alexandria needs an immutable dependency source, while CLI
users need native installation paths that do not require this repository or a
Rust toolchain. The existing Python service and package use date versions and
the `vYYYY-MM-DD` tag family; Rust libraries need SemVer and must not imply that
every service deployment changes their API.

Registry name availability was checked immediately before this decision. Cargo
package names are first-come-first-served and must be rechecked at the
separately authorized first publication.

## Decision

### Versions and identities

- Python/service releases retain `YYYY.M.D` and `vYYYY-MM-DD`.
- The Rust contracts, client, and CLI use an independent SemVer release train.
  They remain lockstep through the pre-1.0 period so one Rust tag and candidate
  manifest identifies the complete tested set.
- Rust release tags use `rust-vMAJOR.MINOR.PATCH`; the first candidate is
  `rust-v0.1.0`.
- crates.io package identities are `supply-chain-monkey-contracts`,
  `supply-chain-monkey-client`, and `supply-chain-monkey-cli`. Their Rust
  library imports remain `scm_contracts` and `scm_client`; the CLI binary
  remains `scm`.
- Inter-crate dependencies use exact versions during the pre-1.0 lockstep
  train. Publication order is contracts, client, then CLI. Each upload waits
  for the preceding version to resolve from the registry before the next
  registry-backed dry run and upload.
- `scm-codegen` remains unpublished.

### Primary release artifacts

crates.io is the library source and also supports `cargo install
supply-chain-monkey-cli --locked`. GitHub Releases are the primary native CLI
binary source. A Rust release is built only from its reviewed tag and attaches:

- the three `.crate` archives and their candidate manifest;
- `scm` archives for `x86_64-pc-windows-msvc`, `x86_64-apple-darwin`,
  `aarch64-apple-darwin`, `x86_64-unknown-linux-gnu`, and
  `aarch64-unknown-linux-gnu` after each target's executable tests pass;
- license/readme files, a machine-readable release manifest, SHA-256 checksums,
  and SPDX or CycloneDX SBOMs; and
- GitHub artifact attestations binding the downloadable archives and manifest
  to the tag, commit, and release workflow.

The release workflow promotes the exact reviewed candidate bytes. It does not
rebuild a candidate after acceptance. The CLI has no self-update mechanism;
upgrade and rollback belong to the selected installer or an explicit archived
version.

### Package-manager rollout

1. **Windows:** publish the tested MSVC archive on GitHub first. Add a portable
   `Wavenumber.SupplyChainMonkey` WinGet manifest only after clean install,
   PATH exposure, upgrade, uninstall, and rollback tests consume that exact
   archive. Validate locally and submit through the community repository's
   reviewed PR flow.
2. **macOS:** publish Intel and Apple Silicon archives first. Add a formula and
   bottles in a Wavenumber-owned Homebrew tap after clean Intel/Apple Silicon
   install, upgrade, rollback, certificate-root, and proxy tests. Homebrew/core
   is a later adoption decision, not a first-release dependency.
3. **Linux:** publish glibc x86-64 and ARM64 archives plus crates.io installation
   first. The Wavenumber Homebrew tap may support Linux when the same tests pass.
   Debian, RPM, Alpine/musl, Nix, Snap, AUR, and other distro-specific channels
   are deferred until supported-user demand and target-specific install/update
   ownership justify them. A command-line tool is not packaged as AppImage.

No package-manager manifest may contain credentials or a deployment URL.
Package managers consume immutable public release URLs and exact hashes.

## Release gates

Before first publication or any later Rust release:

- pass TypeSpec/Python/Rust freshness, cross-language vectors, the complete
  locked Rust gate, and the three-OS client CI matrix;
- build, retain, inventory, hash, and independently review exact crate and CLI
  candidates from a clean tag commit;
- run `cargo publish --dry-run --locked` against crates.io in dependency order;
- install and execute each native archive on its target without a source
  checkout, Python, Node, or Rust toolchain;
- prove credential, URL, diagnostic, archive-path, TLS, redirect, private-root,
  proxy, timeout, cancellation, and response-bound behavior; and
- verify checksums, SBOMs, provenance attestations, update, and rollback before
  activating a downstream package-manager manifest.

## Consequences

Alexandria can eventually pin a published exact client version without a
machine path. Rust API releases are not forced to copy the service's calendar
version. GitHub archives serve ordinary CLI users, while crates.io remains a
developer-oriented source build path. WinGet, Homebrew, and distro-specific
work cannot delay the initial library boundary and are not claimed complete by
this ADR.

## References

- [Cargo publishing](https://doc.rust-lang.org/cargo/reference/publishing.html)
- [Cargo binary installation](https://doc.rust-lang.org/stable/cargo/commands/cargo-install.html)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- [WinGet manifest authoring](https://learn.microsoft.com/en-us/windows/package-manager/package/manifest)
- [WinGet community submission](https://learn.microsoft.com/en-us/windows/package-manager/package/repository)
- [Homebrew taps](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
- [Homebrew bottles](https://docs.brew.sh/Bottles)
