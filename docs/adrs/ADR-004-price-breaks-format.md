# ADR-004: Price Breaks Format Standardization

## Status

Proposed

## Context

Price break data is inconsistent across providers:

- JLC API returns: `[{"qty": 1, "price": 0.50}]` (dicts)
- Mouser returns: `[(1, 0.50)]` (tuples)
- Digikey returns: `[{"qty": 1, "price": 0.50}]` (dicts, but often only unit price)
- LCSC scraper: no pricing data

This makes it impossible for a client to handle price breaks generically without
knowing which provider returned the data.

## Decision

Standardize `price_breaks` as `list[dict]` with this shape:

```python
{
    "qty": int,        # minimum order quantity for this tier
    "unit_price": float,  # price per unit at this tier
    "currency": str    # ISO 4217 currency code, default "USD"
}
```

All providers must convert to this format during their conversion step. If a provider
cannot supply pricing, `price_breaks` remains an empty list.

Rename the dict key from `"price"` to `"unit_price"` for clarity.

## Consequences

- Clients can process price breaks from any provider identically
- Mouser adapter changes from tuples to dicts
- JLC adapter renames `"price"` to `"unit_price"` and adds `"currency"`
- Digikey adapter normalizes its pricing into the same shape
- Empty list remains the indicator for "no pricing available"
