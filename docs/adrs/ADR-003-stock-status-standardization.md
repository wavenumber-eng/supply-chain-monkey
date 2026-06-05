# ADR-003: Stock Status Standardization

## Status

Accepted.

## Decision

Supplier part responses include both `stock_quantity` and `stock_status`.

Valid `stock_status` values:

- `in_stock`: stock quantity is known and greater than zero
- `out_of_stock`: supplier confirms zero available
- `unknown`: stock data is unavailable or unparseable
- `discontinued`: supplier lifecycle data indicates the part is discontinued

`stock_quantity` remains an integer and defaults to `0`.

## Policy

Provider adapters normalize supplier-specific inventory values before returning
`SupplierPartInfo`. Consumers must use `stock_status` when they need to
distinguish confirmed zero stock from unknown stock.

## Consequences

- Consumers can filter and sort availability without guessing from quantity.
- Unavailable inventory data does not masquerade as confirmed zero stock.
- Provider adapters own supplier-specific stock parsing.
