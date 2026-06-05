# Supply Chain Monkey Requirements

This document defines numbered requirements for Supply Chain Monkey. The PyPI
distribution is `supply-chain-monkey`; the Python import package is `scm`.
Requirements can be referenced in code, tests, and commits using their IDs.

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

**Requirement**: Supplier credentials MUST be read from process environment
variables through the central `scm.server.settings` module. Provider modules
must not scan the filesystem or load `.env` files at import time.

**Environment Variables**:
- `DIGIKEY_CLIENT_ID` - Digikey OAuth client ID
- `DIGIKEY_CLIENT_SECRET` - Digikey OAuth client secret
- `MOUSER_API_KEY` - Mouser API key

**Loading**:
```python
from scm.server.settings import settings

client_id = settings.digikey_client_id
```

**Rationale**: Appliku and other service hosts inject credentials at container
runtime. Local development can still pass `.env` through `uvicorn --env-file`,
but credential loading is not a provider side effect.

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

## Service Requirements (REQ-SVC)

### REQ-SVC-001: FastAPI HTTP Service

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | HIGH |
| **Added** | 2026-03-25 |

**Requirement**: The service MUST expose a versioned HTTP API via FastAPI, deployed as a standalone application via Appliku.

**Endpoints (v1)**:
- `GET /v1/health` - Service health check
- `GET /v1/providers/status` - Provider availability status
- `GET /v1/search?supplier=<name>&mpn=<mpn>` - Search by MPN
- `GET /v1/detail?supplier=<name>&part=<part_number>` - Get part details

**Constraints**:
- App binds to `0.0.0.0:8000`
- All endpoints require bearer token authentication
- `supplier` parameter is required on search and detail endpoints
- Responses use standardized envelope (see REQ-SVC-003)

**Rationale**: Centralizes vendor credentials and access behind a single internal API.

**Verification**:
- [ ] FastAPI app starts and serves requests
- [ ] All endpoints return correct response shapes
- [ ] Auth enforced on all endpoints except health

---

### REQ-SVC-002: Bearer Token Authentication

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | HIGH |
| **Added** | 2026-03-25 |

**Requirement**: All API endpoints (except `GET /v1/health`) MUST require a valid bearer token in the `Authorization` header.

**v1 implementation**: Single token stored as `SCM_SERVICE_TOKEN` env var.

**Later**: Per-client tokens with name/scope metadata.

**Error response** for invalid/missing token:
```json
{"detail": "Invalid or missing token"}
```
HTTP 401 Unauthorized.

**Rationale**: Prevents unauthorized access to vendor APIs and rate limits.

**Verification**:
- [ ] Requests without token return 401
- [ ] Requests with invalid token return 401
- [ ] Requests with valid token succeed
- [ ] Health endpoint works without token

---

### REQ-SVC-003: Response Envelope

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | HIGH |
| **Added** | 2026-03-25 |
| **ADR** | ADR-005 |

**Requirement**: All API responses MUST use a standard envelope containing metadata alongside the data payload.

**Envelope fields**:
- `status`: `"ok"`, `"not_found"`, `"provider_error"`
- `supplier`: Provider name
- `provider_latency_ms`: Time spent calling upstream provider
- `service_timestamp`: ISO 8601 UTC timestamp
- `cached`: Whether response came from cache (always `false` in v1)
- `data`: Part data (object for detail, list for search)
- `error`: Error message when status is not `"ok"`, null otherwise

**Rationale**: Clients need timing, status, and cache info for operational decisions.

**Verification**:
- [ ] All endpoints return envelope format
- [ ] `provider_latency_ms` accurately measures upstream call time
- [ ] `status` correctly reflects provider outcome

---

### REQ-SVC-004: Stock Status Standardization

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | MEDIUM |
| **Added** | 2026-03-25 |
| **ADR** | ADR-003 |

**Requirement**: `SupplierPartInfo` MUST include a `stock_status` field alongside `stock_quantity` to distinguish between known stock, unknown stock, and confirmed zero.

**Valid values**: `"in_stock"`, `"out_of_stock"`, `"unknown"`, `"discontinued"`

**Rules**:
- Valid number > 0: `stock_status = "in_stock"`
- Valid number == 0: `stock_status = "out_of_stock"`
- Non-numeric (`"--"`, empty, null): `stock_status = "unknown"`, `stock_quantity = 0`
- Lifecycle discontinued: `stock_status = "discontinued"`

**Rationale**: JLC/LCSC return non-numeric stock values. `stock_quantity = 0` is ambiguous without status.

**Verification**:
- [ ] All providers set `stock_status` during conversion
- [ ] Non-numeric stock values produce `"unknown"` status
- [ ] API response includes both `stock_quantity` and `stock_status`

---

### REQ-SVC-005: Price Breaks Standardization

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | MEDIUM |
| **Added** | 2026-03-25 |
| **ADR** | ADR-004 |

**Requirement**: `price_breaks` MUST use a consistent dict format across all providers.

**Format**:
```python
{"qty": int, "unit_price": float, "currency": str}
```

**Replaces**: Mixed dict/tuple formats currently used across providers.

**Rationale**: Clients must process pricing from any provider without knowing the source.

**Verification**:
- [ ] All providers output dicts with `qty`, `unit_price`, `currency`
- [ ] Mouser converted from tuples to dicts
- [ ] JLC `"price"` key renamed to `"unit_price"`

---

### REQ-SVC-006: Credentials from Settings

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | HIGH |
| **Added** | 2026-03-25 |
| **ADR** | ADR-006 |

**Requirement**: All provider credentials MUST be loaded from a central `settings.py` module that reads `os.environ` at startup. No module-level `.env` file scanning.

**Replaces**: `env.py` and `ensure_env_loaded()` calls at import time.

**Env vars**:
- `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`
- `MOUSER_API_KEY`
- `JLCPCB_APP_ID`, `JLCPCB_ACCESS_KEY`, `JLCPCB_SECRET_KEY`
- `SCM_SERVICE_TOKEN`

**Rationale**: Service gets env vars from container runtime, not filesystem scanning.

**Verification**:
- [ ] `env.py` removed
- [ ] No `ensure_env_loaded()` calls in provider modules
- [ ] All credentials sourced from `settings.py`

---

### REQ-SVC-007: Parallel Client Requests

| Field | Value |
|-------|-------|
| **Status** | APPROVED |
| **Priority** | MEDIUM |
| **Added** | 2026-03-25 |
| **ADR** | ADR-007 |

**Requirement**: The API MUST support clients making concurrent per-provider requests. Each endpoint handles exactly one provider per request.

**Pattern**: Client sends separate requests per provider and handles concurrency:
```
GET /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR
GET /v1/search?supplier=digikey&mpn=TPS543620RPYR
GET /v1/search?supplier=mouser&mpn=TPS543620RPYR
```

**Rationale**: Simpler than server-side fan-out. Client controls which providers to query.

**Verification**:
- [ ] `supplier` is a required parameter
- [ ] Concurrent requests to different providers work correctly
- [ ] No shared mutable state between provider calls

---

## References

- `CLAUDE.md` - Development directives
- `docs/adrs/` - Architecture Decision Records
- `docs/plans/SUPPLY_CHAIN_MONKEY_SERVICE_TRANSITION_PLAN.md` - Migration plan
