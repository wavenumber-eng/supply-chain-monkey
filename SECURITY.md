# Security

Do not report supplier credentials, service tokens, or deployment secrets in
public issues or commits. Rotate any exposed credential immediately.

The service reads credentials from environment variables supplied by the
runtime host. Local `.env` files must remain untracked.
