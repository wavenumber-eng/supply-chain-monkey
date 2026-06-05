# Supply Chain Monkey Contracts

The public contract is implemented by:

- `scm.models.PartResponse`
- `scm.models.ServiceEnvelope`
- `scm.models.SupplierType`
- `scm.client.SCMClient`

The HTTP surface is exposed under `/v1/` by the FastAPI app in
`scm.server.main`.
