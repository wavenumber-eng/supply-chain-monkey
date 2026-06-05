# ADR-004: Price Breaks Format Standardization

## Status

Accepted.

## Decision

Supplier price breaks use a list of dictionaries:

```python
{
    "qty": int,
    "unit_price": float,
    "currency": str,
}
```

`currency` defaults to `USD` when a supplier does not provide a currency.
Providers that cannot supply pricing return an empty list.

## Policy

Provider adapters must normalize supplier-specific pricing data before returning
`SupplierPartInfo`. Consumers should not branch on supplier-specific price break
formats.

## Consequences

- Clients can compare price tiers across suppliers with one parser.
- Missing pricing is represented by an empty list.
- Supplier-specific API payloads remain available only through raw/debug data
  when explicitly requested.
