# Security

Do not report supplier credentials, service tokens, or deployment secrets in
public issues or commits. Rotate any exposed credential immediately.

The service reads credentials from environment variables supplied by the
runtime host. Local `.env` files must remain untracked.

## October 2026 emSign CA incident

The [Python incident notice](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
requires updated certificate bundles and package installers. SCM's supplier
requests and Python client use Certifi through Requests. The project requires
`certifi>=2026.10.19` and `uv>=0.13.4`; CI installs that fixed uv release.
The Rust lockfile also updates `webpki-root-certs` to `1.0.10`, which
[removes the affected root](https://github.com/rustls/webpki-roots/releases/tag/v%2F1.0.10).
It uses `rustls-webpki` `0.103.16` to
[reject the compromised intermediate keys](https://github.com/rustls/webpki/releases/tag/v%2F0.103.16).
Existing Rust consumers must refresh their own lockfiles and rebuild.
The TypeSpec toolchain pins Node `24.22.1`, whose bundled roots also address
this incident. Update local Node installations to match `.node-version`.

### Developer environments

First update the host's OS certificate store. Then bootstrap a standalone uv
installation using that updated store, and sync the project:

```powershell
uv --system-certs self update 0.13.4
uv --version
uv sync --locked --group dev
```

For package-manager installations of uv, update through that package manager.
For every Python environment containing pip, update pip separately: pip's
vendored CA bundle is unaffected by upgrading the environment's Certifi or OS
trust store. The Python notice provides this hash-verified bootstrap:

```powershell
python -m pip install --no-deps --upgrade "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
python -m pip install --upgrade "certifi>=2026.10.19"
```

Repeat for each affected interpreter/virtual environment. Update Python itself
to refresh the pip bundled by `ensurepip` for future environments. Review any
custom `SSL_CERT_FILE`, `SSL_CERT_DIR`, or `REQUESTS_CA_BUNDLE` as well.

### Appliku rollout

Keep the managed `python-3.13-uv` image. Before deploying, confirm the managed
image supplies `uv>=0.13.4`, `pip>=26.2.2` wherever pip is installed, and an OS
CA package updated for this incident. An old uv will fail the project's version
requirement; have the managed image refreshed before retrying.

Rebuild with Docker layer caching disabled and pull refreshed base images;
restart every service instance on the new image. Verify in the built image
and running service environment:

```bash
uv --version
python -m pip --version  # if pip is installed
python -c 'import certifi; print(certifi.__version__, certifi.where())'
```

Run the full L99 signoff before a production PR, then check `/v1/health` after
deployment. A passing local signoff does not verify the deployed image's OS
trust store or build tools. Updating `uv.lock` alone does not complete rollout.

The optional Dockerfile pins fixed uv, refreshes OS certificates, and upgrades
pip using uv. Release and signoff builds also use `build --installer uv` to
avoid bootstrapping an old pip in an isolated build environment.
