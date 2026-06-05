# ADR-006: Credentials Loaded from Settings

## Status

Accepted.

## Decision

Supplier credentials and service authentication values are read through
`scm.server.settings`.

Provider modules must not:

- scan the filesystem for `.env` files
- mutate `os.environ` at import time
- load credentials independently of service settings

Local development may use `uvicorn --env-file .env` or equivalent process-level
environment setup.

## Consequences

- Production configuration is owned by the deployment host.
- Provider adapters are easier to test because credentials are passed through
  construction/configuration.
- Importing provider modules has no credential-loading side effects.
