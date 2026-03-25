# Supply Chain Monkey Requirements

This document defines numbered requirements for the `supply_chain_monkey` module. Requirements can be referenced in code, tests, and commits using their IDs.

## Requirement Categories

| Prefix | Category | Description |
|--------|----------|-------------|
| `REQ-ENUM` | Enumeration | SupplierType enum design |
| `REQ-DATA` | Data Models | SupplierPartInfo structure |
| `REQ-INTERFACE` | Interface | SupplierInterface ABC design |
| `REQ-FACTORY` | Factory Pattern | Supplier instantiation |
| `REQ-LAZY` | Lazy Loading | Import optimization |
| `REQ-PARALLEL` | Parallel Execution | Multi-supplier search |
| `REQ-VARIANT` | Variant Selection | Packaging preference logic |
| `REQ-CRED` | Credentials | Authentication and secrets |
| `REQ-ERROR` | Error Handling | Graceful degradation |
| `REQ-TEST` | Testing | Test coverage and patterns |
| `REQ-EXTEND` | Extensibility | Adding new suppliers |

## Requirement Status

| Status | Meaning |
|--------|---------|
| `DRAFT` | Proposed, under discussion |
| `APPROVED` | Accepted, not yet implemented |
| `IMPLEMENTED` | Code complete with tests |
| `DEPRECATED` | No longer applicable |

---

## Enumeration Requirements (REQ-ENUM)

### REQ-ENUM-001: Supplier Type Enumeration

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supported suppliers MUST be defined in `SupplierType` enum for type-safe identification.

**Enum Definition**:
```python
class SupplierType(Enum):
    JLCPCB = "JLCPCB"
    LCSC = "LCSC"
    DIGIKEY = "Digikey"
    MOUSER = "Mouser"
```

**Usage**:
- Factory pattern: `create_supplier(SupplierType.JLCPCB)`
- Result identification: `part.supplier == SupplierType.JLCPCB`
- Iteration: `for supplier_type in get_available_suppliers()`

**Rationale**: Type-safe supplier identification prevents typos, enables IDE autocomplete, supports exhaustive pattern matching.

**Verification**:
- [x] `SupplierType` enum defined
- [x] All implemented suppliers have enum value
- [x] Factory function uses enum for dispatch

---

## Data Model Requirements (REQ-DATA)

### REQ-DATA-001: Standardized Part Information Container

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supplier implementations MUST return data in standardized `SupplierPartInfo` dataclass format.

**Required Fields**:
- `supplier: SupplierType` - Supplier identification
- `supplier_part_number: str` - Supplier's unique ID
- `manufacturer: str` - Manufacturer name
- `manufacturer_part_number: str` - MPN

**Optional Fields**:
- `description: str` - Part description
- `datasheet_url: str` - Datasheet link
- `product_url: str` - Product page link
- `stock_quantity: int` - Available stock
- `price_breaks: list[dict]` - Pricing tiers
- `lifecycle_status: str` - Active/Obsolete/NRND
- `extra_data: dict` - Supplier-specific fields

**Rationale**: Normalizes disparate supplier APIs into common format for consuming code.

**Verification**:
- [x] `SupplierPartInfo` dataclass defined
- [x] All suppliers return `SupplierPartInfo` objects
- [x] `to_dict()` method for serialization

---

### REQ-DATA-002: Price Breaks Format

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Price breaks MUST use standardized list-of-dicts format with `qty` and `price` keys.

**Format**:
```python
price_breaks = [
    {"qty": 1, "price": 0.50},
    {"qty": 10, "price": 0.45},
    {"qty": 100, "price": 0.40}
]
```

**Rationale**: Consistent format enables price comparison across suppliers.

**Verification**:
- [x] Digikey implementation uses standardized format
- [ ] JLCPCB/LCSC implementations (not yet extracting pricing)

---

## Interface Requirements (REQ-INTERFACE)

### REQ-INTERFACE-001: Abstract Base Class Compliance

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supplier implementations MUST inherit from `SupplierInterface` ABC and implement all abstract methods.

**Required Methods**:
1. `supplier_type` property - Returns `SupplierType` enum
2. `parameter_field_name` property - Returns Part parameter field name
3. `search_by_mpn(mpn, **kwargs)` - Search by MPN, return list
4. `get_part_details(supplier_pn, **kwargs)` - Get details, return single result or None

**Signature Constraints**:
- `search_by_mpn()` MUST return `list[SupplierPartInfo]` (empty list on error)
- `get_part_details()` MUST return `SupplierPartInfo | None` (None on error)
- Both methods MUST accept `**kwargs` for extensibility

**Rationale**: Ensures all suppliers provide same functionality with identical signatures.

**Verification**:
- [x] `SupplierInterface` ABC defined with abstract methods
- [x] All implemented suppliers inherit from ABC
- [x] Tests verify method signatures and return types

---

### REQ-INTERFACE-002: Parameter Field Name Mapping

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Each supplier MUST define `parameter_field_name` property mapping to Part parameter field.

**Mapping**:
- JLCPCB → `"JLCPCB Part #"`
- LCSC → `"LCSC Part #"`
- Digikey → `"Digikey Part #"`
- Mouser → `"Mouser Part #"`

**Usage**: Auto-fill Part parameter fields after search.

**Rationale**: Decouples supplier implementations from Part field naming conventions.

**Verification**:
- [x] All suppliers define `parameter_field_name`
- [x] Field names remain stable for downstream consumers

---

## Factory Pattern Requirements (REQ-FACTORY)

### REQ-FACTORY-001: Centralized Supplier Instantiation

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supplier instances MUST be created via `create_supplier()` factory function.

**Factory Signature**:
```python
def create_supplier(supplier_type: SupplierType, **credentials) -> SupplierInterface:
    """
    Create supplier instance.

    Args:
        supplier_type: Type of supplier to create
        **credentials: Supplier-specific credentials

    Returns:
        Configured SupplierInterface implementation

    Raises:
        NotImplementedError: If supplier not implemented
    """
```

**Dispatch Pattern**:
```python
if supplier_type == SupplierType.JLCPCB:
    from .jlcpcb_supplier import JLCPCBSupplier
    return JLCPCBSupplier(**credentials)
```

**Rationale**:
- Hides implementation details
- Enables lazy loading (import only when needed)
- Single point for instantiation logic (logging, caching, etc.)

**Verification**:
- [x] Factory function defined
- [x] All suppliers creatable via factory
- [x] Invalid supplier_type raises `NotImplementedError`

---

## Lazy Loading Requirements (REQ-LAZY)

### REQ-LAZY-001: Deferred Import of Supplier Implementations

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Supplier implementation modules MUST be imported lazily via `__getattr__()` hook in `__init__.py`.

**Implementation**:
```python
def __getattr__(name: str):
    """Lazy import for supplier implementations."""
    if name == "JLCPCBSupplier":
        from .jlcpcb_supplier import JLCPCBSupplier
        return JLCPCBSupplier
    # ... other suppliers ...
    raise AttributeError(f"module has no attribute {name!r}")
```

**Rationale**:
- Faster import time (don't load all suppliers upfront)
- Reduced memory usage (only load what's used)
- Credential loading deferred (no unnecessary API calls)

**Verification**:
- [x] `__getattr__()` hook implemented
- [x] Suppliers imported only when accessed
- [x] Import time reduced (measured)

---

## Parallel Execution Requirements (REQ-PARALLEL)

### REQ-PARALLEL-001: Multi-Supplier Parallel Search

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: Multi-supplier search MUST execute searches in parallel using ThreadPoolExecutor to minimize total search time.

**Architecture**:
- One thread per supplier
- Concurrent execution (not sequential)
- Results collected after all threads complete
- GUI updates thread-safe via deferred execution

**Performance Targets**:
| Suppliers | Sequential | Parallel | Speedup |
|-----------|-----------|----------|---------|
| 2 suppliers | ~3.2s | ~1.8s | 1.8x |
| 3 suppliers | ~4.3s | ~1.8s | 2.4x |
| 4 suppliers | ~5.5s | ~2.0s | 2.8x |

**Rationale**: Network I/O dominates search time. Parallelization provides near-linear speedup.

**Verification**:
- [x] `search_all_suppliers()` uses ThreadPoolExecutor
- [x] Performance targets met (benchmarked)
- [x] Thread-safe GUI updates

---

### REQ-PARALLEL-002: Thread-Safe GUI Updates

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: GUI updates from worker threads MUST use thread-safe deferred execution (DearPyGUI `split_frame()`).

**Pattern**:
```python
def update_status(status: str):
    """Thread-safe GUI update."""
    dpg.split_frame()  # Defer to next frame
    dpg.set_value("status_text", status)
```

**Rationale**: DearPyGUI (and most GUI frameworks) are not thread-safe. Direct updates from threads cause crashes.

**Verification**:
- [x] All GUI updates use `dpg.split_frame()`
- [x] No race conditions observed
- [x] Stress tested with parallel searches

---

## Variant Selection Requirements (REQ-VARIANT)

### REQ-VARIANT-001: Cut Tape Preference for Digikey

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Digikey search results MUST automatically prefer Cut Tape variants (`-CT-ND` suffix) for prototyping use cases.

**Selection Logic**:
1. If multiple results for same MPN, prefer variant with `-CT-ND` suffix
2. If no Cut Tape variant, use first result
3. User can override via GUI dropdown

**Variant Types**:
- **Cut Tape** (`-CT-ND`) - Small quantities, no reel
- **Tape & Reel** (`-TR-ND`) - 1000+ units, reel packaging
- **Digi-Reel** (`-DKR-ND`) - Custom reel size

**Rationale**: Prototyping typically needs 1-100 units. Cut Tape is most convenient (no minimum order, easy handling).

**Verification**:
- [x] Cut Tape preference implemented
- [x] Fallback to first result if no CT variant
- [x] GUI allows manual override

---

### REQ-VARIANT-002: Extensible Variant Preferences

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | LOW |
| **Added** | 2025-12-19 |

**Requirement**: Variant selection logic MUST be extensible for additional supplier-specific preferences.

**Future Preferences**:
- Stock-aware: Prefer in-stock variants
- Price-aware: Prefer cheapest variant for quantity needed
- Lead-time aware: Prefer variants with shortest lead time

**Rationale**: Different use cases need different selection strategies.

**Verification**:
- [ ] Variant selection abstracted to configurable function
- [ ] Preferences configurable per supplier

---

## Credential Requirements (REQ-CRED)

### REQ-CRED-001: Environment Variable Credentials

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: Supplier credentials MUST be loaded from environment variables via a local `.env` helper in `supply_chain_monkey`.

**Environment Variables**:
- `DIGIKEY_CLIENT_ID` - Digikey OAuth client ID
- `DIGIKEY_CLIENT_SECRET` - Digikey OAuth client secret
- `MOUSER_API_KEY` - Mouser API key

**Loading**:
```python
import os
from supply_chain_monkey.env import ensure_env_loaded

ensure_env_loaded()
client_id = os.getenv("DIGIKEY_CLIENT_ID")
```

**Rationale**: `.env` file in `.gitignore` prevents committing secrets to repo.

**Verification**:
- [x] Credentials loaded from environment
- [x] `.env` file in `.gitignore`
- [x] Missing credentials handled gracefully (supplier skipped)

---

### REQ-CRED-002: No Credentials in Code

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: Credentials MUST NEVER be hardcoded in source code or logged.

**Forbidden**:
```python
# WRONG - hardcoded credentials
api_key = "abc123xyz"

# WRONG - logging credentials
log.info(f"Using API key: {api_key}")
```

**Allowed**:
```python
# CORRECT - from environment
api_key = os.getenv("DIGIKEY_API_KEY")

# CORRECT - masked logging
log.info(f"Using API key: {api_key[:4]}..." if api_key else "No API key")
```

**Rationale**: Security best practice, prevents credential leaks.

**Verification**:
- [x] Code review for hardcoded secrets
- [x] Logs reviewed for credential exposure

---

## Error Handling Requirements (REQ-ERROR)

### REQ-ERROR-001: Graceful Degradation on Errors

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supplier methods MUST handle errors gracefully by returning empty results (not raising exceptions).

**Error Handling Pattern**:
```python
def search_by_mpn(self, mpn: str, **kwargs) -> list[SupplierPartInfo]:
    try:
        # API call
        response = requests.get(...)
        return parse_results(response)
    except Exception as e:
        log.warning(f"Error searching {self.supplier_type.value}: {e}")
        return []  # Empty list, not exception
```

**Error Types**:
- Missing credentials → skip supplier, log info
- Network timeout → return empty list, log warning
- API rate limit → return empty list, log warning
- Invalid MPN → return empty list, log info
- Scraping failure → return empty list, log error

**Rationale**: One supplier failure should not block others in parallel search.

**Verification**:
- [x] All methods catch exceptions
- [x] Empty results returned on error
- [x] Errors logged at appropriate level

---

### REQ-ERROR-002: Logging Level Standards

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Error logging MUST follow standardized logging levels.

**Logging Levels**:
- `log.debug()` - API requests, responses, low-level details
- `log.info()` - Search initiated, results found, normal operations
- `log.warning()` - Timeouts, rate limits, missing credentials, recoverable errors
- `log.error()` - Unexpected errors, scraping failures, unrecoverable errors

**Examples**:
```python
log.debug(f"API request: GET {url}")
log.info(f"Found {len(results)} results for {mpn}")
log.warning(f"Missing credentials for {supplier_type.value}, skipping")
log.error(f"Scraping failed: {e}")
```

**Rationale**: Consistent logging enables debugging and monitoring.

**Verification**:
- [x] All suppliers use consistent logging levels
- [x] Logs reviewed for appropriate levels

---

## Testing Requirements (REQ-TEST)

### REQ-TEST-001: Interface Compliance Tests

| Field | Value |
|-------|-------|
| **Status** | IMPLEMENTED |
| **Priority** | HIGH |
| **Added** | 2025-12-19 |

**Requirement**: All supplier implementations MUST have tests verifying compliance with `SupplierInterface`.

**Required Tests**:
- `test_supplier_type()` - Verify correct `SupplierType` returned
- `test_parameter_field_name()` - Verify correct field name
- `test_search_by_mpn_returns_list()` - Verify list return type
- `test_get_part_details_returns_single_or_none()` - Verify return type

**Test Pattern**:
```python
def test_jlcpcb_implements_interface():
    """REQ-INTERFACE-001: JLCPCB implements SupplierInterface."""
    supplier = create_supplier(SupplierType.JLCPCB)
    assert isinstance(supplier, SupplierInterface)
    assert supplier.supplier_type == SupplierType.JLCPCB
    assert isinstance(supplier.parameter_field_name, str)
```

**Verification**:
- [x] Tests for JLCPCB, LCSC, Digikey
- [ ] Tests for Mouser (less mature)

---

### REQ-TEST-002: Mock External Dependencies

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Unit tests MUST mock external HTTP requests to avoid dependency on supplier API availability.

**Mocking Strategy**:
- Use `responses` library for HTTP mocking
- Fixture JSON files for API responses
- Test-only environment variables for credentials

**Pattern**:
```python
import responses

@responses.activate
def test_digikey_search():
    """REQ-INTERFACE-001: Digikey search returns results."""
    # Mock API response
    responses.add(
        responses.GET,
        "https://api.digikey.com/...",
        json={"results": [...]},
        status=200
    )

    supplier = create_supplier(SupplierType.DIGIKEY, client_id="test", client_secret="test")
    results = supplier.search_by_mpn("STM32F407VGT6")
    assert len(results) > 0
```

**Verification**:
- [ ] HTTP requests mocked in unit tests
- [ ] Integration tests use real APIs (with rate limiting)

---

## Extensibility Requirements (REQ-EXTEND)

### REQ-EXTEND-001: Adding New Suppliers

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | MEDIUM |
| **Added** | 2025-12-19 |

**Requirement**: Adding a new supplier MUST NOT require changes to consuming code, only changes to supplier module.

**Steps**:
1. Add enum value to `SupplierType`
2. Create implementation inheriting `SupplierInterface`
3. Register in `create_supplier()` factory
4. Add to `IMPLEMENTED_SUPPLIERS` list
5. Add lazy loading in `__init__.py`
6. Write tests

**Verification**:
- [x] Step-by-step guide in ARCHITECTURE.md
- [x] Four suppliers added using this pattern

---

## References

- `ARCHITECTURE.md` - Architecture principles and design patterns
- `README.md` - User-facing documentation and quick start guide
- `docs/` - Supplier-specific documentation
