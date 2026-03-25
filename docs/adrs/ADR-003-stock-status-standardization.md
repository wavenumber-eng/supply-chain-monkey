# ADR-003: Stock Status Standardization

## Status

Proposed

## Context

Vendors report stock inconsistently:

- JLCPCB/LCSC sometimes return `"--"`, empty string, or non-numeric values for stock
- The current code silently converts these to `0` via `_to_int()`
- A `stock_quantity` of `0` is ambiguous: does it mean "confirmed zero in stock" or
  "stock data unavailable"?

Downstream consumers (lib_cruncher, bom_cruncher) need to distinguish between:

1. Part in stock with a known quantity
2. Part exists but stock is unknown or unavailable
3. Part is out of stock (confirmed zero)
4. Part not found at all

## Decision

Add a `stock_status` field to `SupplierPartInfo`:

```python
stock_status: str = "unknown"
```

Valid values:

| Value | Meaning |
|---|---|
| `"in_stock"` | Stock quantity is known and > 0 |
| `"out_of_stock"` | Vendor confirmed zero available |
| `"unknown"` | Stock data unavailable or unparseable |
| `"discontinued"` | Part is discontinued by vendor |

Rules:

- `stock_quantity` remains an `int`, defaults to `0`
- When stock data is a valid number > 0: `stock_status = "in_stock"`
- When stock data is a valid number == 0: `stock_status = "out_of_stock"`
- When stock data is `"--"`, empty, or unparseable: `stock_status = "unknown"`, `stock_quantity = 0`
- When lifecycle indicates discontinued: `stock_status = "discontinued"`

Each provider adapter is responsible for setting both fields correctly during
conversion.

## Consequences

- API consumers can filter/sort on `stock_status` without guessing
- No breaking change to `stock_quantity` — it stays `int`
- Providers need a small update to their conversion methods
- Response envelope includes both fields
