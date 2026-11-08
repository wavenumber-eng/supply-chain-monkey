# Account data API proposal

**Status:** The JLC My Parts Lib inventory slice is implemented in this worktree. See [ADR-013](../../adrs/ADR-013-jlc-private-inventory.md) for the current contract and limits. Everything below is future work.

The [account data research](../../research/2026-11-02-account-data-api-review.md) records what the supplier APIs expose and what still needs verification. SCM owns supplier credentials. Callers use the existing SCM bearer token.

## Current boundary

The read-only `/v1/account/capabilities`, `/v1/account/inventory`, and `/v1/account/inventory/lookup` routes cover only JLC My Parts Lib. Inventory scans the bounded live JLC library and returns `items` and `observed_at`. Lookup accepts exactly one `spn` or `mpn` and returns `observed` or `not_observed`. Each row keeps the four JLC balances as separate nullable integer fields; zero and unknown remain distinct. A scan that exceeds a bound returns an error. The routes do not show order transactions, physical inventory at our facilities, or a point-in-time snapshot.

## Future order data

A later API could expose order summaries and detail for JLC PCB and parts orders, then other suppliers. Before defining its contract, verify each supplier's order coverage, date filter timezone, stable row identity, and detail reference. A JLC batch number may identify several board items; a display number may differ from the identifier accepted by the detail API. For LCSC, published API order coverage may differ from website history. The first order API should state these limits in its response rather than imply that an empty list proves no orders exist.

Potential operations are `GET /v1/account/orders` and `GET /v1/account/orders/detail`. Their filters, paging, response fields, and error contract remain undecided. Order records must retain source references and avoid combining distinct lines merely because they share a batch identifier. Financial, address, and file data need a separate data-minimization review before exposure.

## Future inventory sources

DigiKey, Mouser, LCSC, and internal physical stock need separate source verification. Catalog availability, account-visible inventory, and stock physically held in our own locations are different quantities. A multi-supplier contract should include explicit provenance and location only when real adapters can populate them. Do not infer availability to build from a JLC balance name or sum the four balances into an invented total.

## Next validation

Compare a known preordered JLC C-code and its four balances with the My Parts Lib screen. Confirm which bucket represents purchased or reserved quantity for that example. Then decide whether a dedicated order-history API is valuable enough to implement.
