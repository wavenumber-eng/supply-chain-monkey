# Supply Chain Monkey Contracts

The public contract is distributed on PyPI as `supply-chain-monkey` and imported
as `scm`.

Client-side consumers should use:

- `scm.models.PartResponse`
- `scm.models.ServiceEnvelope`
- `scm.models.SupplierType`
- `scm.client.SCMClient`

The deployed server surface is exposed under `/v1/` by the FastAPI app in
`scm.server.main`. Consumer applications must not import provider adapters from
`scm.server.providers`; provider credentials and supplier-specific integration
logic stay server-side.
