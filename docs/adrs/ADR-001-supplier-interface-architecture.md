# ADR-001: Supply Chain Monkey Architecture

This document defines the architectural principles and design patterns for the `supply_chain_monkey` module. All code changes MUST adhere to these principles.

## Design Philosophy

### Core Principles

1. **Supplier Agnostic Interface**
   - All suppliers implement same abstract interface
   - Consuming code works with any supplier using identical API
   - Adding new suppliers requires no changes to consuming code

2. **Standardized Data Format**
   - `SupplierPartInfo` normalizes data from different sources
   - Same fields across all suppliers (stock, pricing, description, etc.)
   - Supplier-specific data stored in `extra_data` dict

3. **Graceful Degradation**
   - Missing credentials: skip supplier (no crash)
   - Network errors: return empty list (log warning)
   - API timeouts: continue with other suppliers
   - Parallel search: one failure does not block others

4. **Lazy Loading**
   - Supplier implementations loaded only when used
   - Improves import time and reduces memory usage
   - Factory pattern hides implementation details

5. **Parallel Execution**
   - Multiple suppliers searched simultaneously (ThreadPoolExecutor)
   - 2-4x faster than sequential search
   - Thread-safe UI updates via deferred execution

## Module Structure

```
supply_chain_monkey/
├── src/py/supply_chain_monkey/      # package code
├── docs/adrs/                       # architecture decisions
├── docs/requirements/               # numbered requirements
├── docs/plans/                      # execution plans
├── docs/research/                   # vendor/API reference material
└── tests/                           # rack suite and helper scripts
```

## Core Components

### 1. Supplier Type Enumeration (REQ-ENUM-001)

**`SupplierType` Enum**:
```python
class SupplierType(Enum):
    JLCPCB = "JLCPCB"
    LCSC = "LCSC"
    DIGIKEY = "Digikey"
    MOUSER = "Mouser"
```

**Purpose**: Type-safe identification of suppliers.

**Usage**:
- Factory pattern: `create_supplier(SupplierType.JLCPCB)`
- Result identification: `part.supplier == SupplierType.JLCPCB`
- Iteration: `for supplier_type in get_available_suppliers()`

### 2. Standardized Data Container (REQ-DATA-001)

**`SupplierPartInfo` Dataclass**:
```python
@dataclass
class SupplierPartInfo:
    # Core identification
    supplier: SupplierType
    supplier_part_number: str
    manufacturer: str
    manufacturer_part_number: str

    # Details
    description: str = ""
    datasheet_url: str = ""
    product_url: str = ""

    # Availability & pricing
    stock_quantity: int = 0
    price_breaks: list[dict[str, Any]] = field(default_factory=list)
    lifecycle_status: str = ""

    # Metadata
    extra_data: dict[str, Any] = field(default_factory=dict)
```

**Field Descriptions**:
- `supplier`: Which supplier this part is from (enum)
- `supplier_part_number`: Supplier's unique ID (e.g., "C2040", "296-12345-1-ND")
- `manufacturer`: Manufacturer name (e.g., "STMicroelectronics")
- `manufacturer_part_number`: MPN (e.g., "STM32F407VGT6")
- `description`: Human-readable description (e.g., "10uF 6.3V X5R 0603")
- `datasheet_url`: Link to PDF datasheet
- `product_url`: Link to supplier's product page
- `stock_quantity`: Available stock (integer)
- `price_breaks`: Quantity pricing tiers `[{"qty": 1, "price": 0.50}, ...]`
- `lifecycle_status`: "Active", "Obsolete", "NRND" (Not Recommended for New Designs)
- `extra_data`: Supplier-specific fields (preserve original API data)

**Rationale**: Normalizes disparate supplier APIs into common format.

### 3. Abstract Base Class (REQ-INTERFACE-001)

**`SupplierInterface` ABC**:
```python
class SupplierInterface(ABC):
    def __init__(self, **credentials):
        self.credentials = credentials

    @property
    @abstractmethod
    def supplier_type(self) -> SupplierType:
        """Return supplier type enum."""
        pass

    @property
    @abstractmethod
    def parameter_field_name(self) -> str:
        """Return Part parameter field name (e.g., 'JLCPCB Part #')."""
        pass

    @abstractmethod
    def search_by_mpn(self, mpn: str, **kwargs) -> list[SupplierPartInfo]:
        """Search by manufacturer part number."""
        pass

    @abstractmethod
    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """Get details for specific supplier part number."""
        pass
```

**Required Methods**:
1. `supplier_type` - Returns `SupplierType` enum value
2. `parameter_field_name` - Returns field name for Part parameter (e.g., "JLCPCB Part #")
3. `search_by_mpn()` - Search by manufacturer part number, return list of matches
4. `get_part_details()` - Get details for specific supplier part number, return single match or None

**Responsibilities**:
- Handle own authentication/credentials
- Return standardized `SupplierPartInfo` objects
- Graceful error handling (return empty list or None, log errors)
- Rate limiting (implementation-specific)

### 4. Factory Pattern (REQ-FACTORY-001)

**`create_supplier()` Function**:
```python
def create_supplier(supplier_type: SupplierType, **credentials) -> SupplierInterface:
    """
    Create supplier instance using factory pattern.

    Args:
        supplier_type: Type of supplier to create
        **credentials: Supplier-specific credentials

    Returns:
        Configured SupplierInterface implementation

    Raises:
        NotImplementedError: If supplier not yet implemented
    """
    if supplier_type == SupplierType.JLCPCB:
        from .jlcpcb_supplier import JLCPCBSupplier
        return JLCPCBSupplier(**credentials)
    elif supplier_type == SupplierType.LCSC:
        from .lcsc_supplier import LCSCSupplier
        return LCSCSupplier(**credentials)
    elif supplier_type == SupplierType.DIGIKEY:
        from .digikey_supplier import DigikeySupplier
        return DigikeySupplier(**credentials)
    elif supplier_type == SupplierType.MOUSER:
        from .mouser_supplier import MouserSupplier
        return MouserSupplier(**credentials)
    else:
        raise NotImplementedError(f"Supplier {supplier_type.value} not yet implemented")
```

**Benefits**:
- Hides implementation details from consuming code
- Enables lazy loading (import only when needed)
- Single point of instantiation (easier to add caching, logging, etc.)

### 5. Lazy Loading (REQ-LAZY-001)

**`__init__.py` `__getattr__()` Hook**:
```python
def __getattr__(name: str):
    """Lazy import for supplier implementations."""
    if name == "JLCPCBSupplier":
        from .jlcpcb_supplier import JLCPCBSupplier
        return JLCPCBSupplier
    elif name == "LCSCSupplier":
        from .lcsc_supplier import LCSCSupplier
        return LCSCSupplier
    # ... etc
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Rationale**:
- Faster import time (don't load all suppliers upfront)
- Reduced memory usage (only load what's used)
- Credentials loaded only when needed (no unnecessary API calls)

## Supplier Implementations

### JLCPCB Supplier

**Implementation**: `jlcpcb_supplier.py`

**Technology**: Web scraping (no official API)

**Credentials**: None required

**Features**:
- Search by MPN
- Get details by C code (e.g., "C2040")
- Stock availability
- Description extraction

**Limitations**:
- No pricing data (scraper does not extract)
- No datasheet links
- Stock numbers may not be real-time
- Scraping may break if JLCPCB updates website

**C Code Format**: C followed by digits (C1, C2040, C668319)

### LCSC Supplier

**Implementation**: `lcsc_supplier.py`

**Technology**: Web scraping (no official API)

**Credentials**: None required

**Features**:
- Search by MPN
- Get details by LCSC part number
- Stock availability
- Description extraction

**Relationship to JLCPCB**: LCSC is JLCPCB's supplier, so many parts overlap.

### Digikey Supplier

**Implementation**: `digikey_supplier.py`

**Technology**: Official Digikey API (REST)

**Credentials**: Required (OAuth 2.0)
- `DIGIKEY_CLIENT_ID`
- `DIGIKEY_CLIENT_SECRET`

**Features**:
- Full API access (search, details, pricing, stock)
- Real-time stock availability
- Complete pricing tiers
- Datasheet links
- Lifecycle status
- Product images

**Variant Selection** (REQ-VARIANT-001):
- Automatically prefers Cut Tape (CT-ND) for prototyping
- Falls back to first result if no Cut Tape variant

**Authentication**: OAuth 2.0 with token caching.

### Mouser Supplier

**Implementation**: `mouser_supplier.py`

**Technology**: Official Mouser API (REST)

**Credentials**: Required (API key)
- `MOUSER_API_KEY`

**Status**: Implemented but less mature than Digikey.

## Parallel Search Architecture (REQ-PARALLEL-001)

**Implementation**: `search_all_suppliers.py`

**Pattern**: ThreadPoolExecutor with GUI integration

**Flow**:
```
1. User initiates search (MPN provided)
2. Create thread pool (one thread per supplier)
3. For each supplier:
   a. Check credentials (skip if missing)
   b. Execute search in thread
   c. Update GUI with status (SEARCHING, OK, ERROR, SKIPPED)
4. Wait for all threads to complete
5. Collect results
6. Apply variant selection logic
7. Return aggregated results
```

**Thread Safety**:
- Each supplier search runs in isolated thread
- GUI updates deferred via `dpg.split_frame()` (DearPyGUI thread-safe update)
- No shared mutable state between threads
- Results collected after all threads complete

**Performance**:
| Suppliers | Sequential | Parallel | Speedup |
|-----------|-----------|----------|---------|
| 2 suppliers | 3.2s | 1.8s | 1.8x |
| 3 suppliers | 4.3s | 1.8s | 2.4x |
| 4 suppliers | 5.5s | 2.0s | 2.8x |

**Rationale**: Most time spent waiting for network I/O, not CPU. Parallelization provides linear speedup.

## Variant Selection Logic (REQ-VARIANT-001)

**Problem**: Some suppliers (Digikey) return multiple packaging variants for same MPN.

**Examples**:
- Cut Tape (CT-ND) - 10-100 units, no minimum order
- Tape & Reel (TR-ND) - 1000+ units, reel packaging
- Digi-Reel (DKR-ND) - Custom reel size

**Selection Strategy**:

**Digikey**:
- Prefer Cut Tape (`-CT-ND` suffix) for prototyping
- Rationale: Small quantities, no reel, easy handling
- Fallback: First result if no Cut Tape variant

**Other Suppliers**:
- Use first result (no variant preferences defined yet)

**User Override**: GUI allows manual selection from dropdown.

**Implementation**:
```python
def select_preferred_variant(results: list[SupplierPartInfo], supplier_type: SupplierType) -> SupplierPartInfo:
    if supplier_type == SupplierType.DIGIKEY:
        # Prefer Cut Tape
        for result in results:
            if result.supplier_part_number.endswith('-CT-ND'):
                return result
    # Fallback: first result
    return results[0] if results else None
```

## Credential Management (REQ-CRED-001)

**Credentials Loaded from `.env` File**:
```bash
# Digikey API
DIGIKEY_CLIENT_ID=your_client_id_here
DIGIKEY_CLIENT_SECRET=your_client_secret_here

# Mouser API
MOUSER_API_KEY=your_api_key_here
```

**Loading**:
- Automatic via `supply_chain_monkey.env.ensure_env_loaded()`
- Suppliers read from environment variables
- Missing credentials: supplier skipped (no error)

**Security**:
- `.env` file in `.gitignore` (not committed to repo)
- Credentials never logged or printed
- OAuth tokens cached securely (Digikey)

## GUI Integration

**Multi-Supplier Search Dialog**:
- DearPyGUI modal dialog
- Supplier status table (name, status, result count, time)
- Result dropdown (select variant if multiple matches)
- Apply/Cancel buttons
- Live updates during search

**Status Indicators**:
- `[SEARCHING]` - Blue, search in progress
- `[OK]` - Green, results found
- `[ERROR]` - Red, search failed
- `[SKIPPED]` - Gray, no credentials or disabled

**Part Parameter Auto-Fill**:
- On Apply: `part[supplier.parameter_field_name] = selected_result.supplier_part_number`
- Example: `part["JLCPCB Part #"] = "C2040"`

## Error Handling (REQ-ERROR-001)

**Graceful Degradation**:
- Missing credentials: skip supplier (log info, no exception)
- Network timeout: return empty list (log warning)
- API rate limit: return empty list (log warning)
- Invalid MPN: return empty list (log info)
- Scraping failure: return empty list (log error)

**Logging Levels**:
- `log.debug()` - API requests, responses
- `log.info()` - Search initiated, results found
- `log.warning()` - Timeouts, rate limits, missing credentials
- `log.error()` - Unexpected errors, scraping failures

**No Exceptions Raised**:
- All supplier methods catch exceptions and return empty/None
- Parallel search: one failure does not block others
- GUI: error status displayed, search continues

## Testing Strategy

### Unit Tests

**Test Coverage**:
- `test_supplier_interface.py` - Interface compliance for all implementations
- `test_digikey_auth.py` - Digikey OAuth flow
- `test_env_loading.py` - Credential loading from .env

**Test Patterns**:
```python
def test_jlcpcb_search_by_mpn():
    """REQ-INTERFACE-001: search_by_mpn returns list of SupplierPartInfo."""
    jlc = create_supplier(SupplierType.JLCPCB)
    results = jlc.search_by_mpn("GCM1555C1H100FA16D")

    assert isinstance(results, list)
    for result in results:
        assert isinstance(result, SupplierPartInfo)
        assert result.supplier == SupplierType.JLCPCB
        assert result.supplier_part_number.startswith("C")
```

### Integration Tests

**Demo Scripts**:
- `demo_parallel_search.py` - Test parallel search performance
- `test_digikey_auth.py` - Manual Digikey OAuth probe

**Manual Testing**:
```bash
cd C:\path\to\supply-chain-monkey

# Parallel search performance test
uv run python tests/scripts/demo_parallel_search.py

# Manual Digikey auth probe
uv run python tests/scripts/test_digikey_auth.py
```

### Mocking Strategy

**External Dependencies**:
- HTTP requests: mock with `responses` library
- API responses: fixture JSON files
- Credentials: test-only env vars

**No Mocking for Integration Tests**: Use real APIs with rate limiting.

## Adding New Suppliers (REQ-EXTEND-001)

### Step-by-Step Guide

**1. Add Enum Value**:
```python
# supplier_interface.py
class SupplierType(Enum):
    JLCPCB = "JLCPCB"
    LCSC = "LCSC"
    DIGIKEY = "Digikey"
    MOUSER = "Mouser"
    ARROW = "Arrow"  # Add here
```

**2. Implement Interface**:
```python
# arrow_supplier.py
class ArrowSupplier(SupplierInterface):
    @property
    def supplier_type(self) -> SupplierType:
        return SupplierType.ARROW

    @property
    def parameter_field_name(self) -> str:
        return "Arrow Part #"

    def search_by_mpn(self, mpn: str, **kwargs) -> list[SupplierPartInfo]:
        # Implementation
        pass

    def get_part_details(self, part_number: str, **kwargs) -> SupplierPartInfo | None:
        # Implementation
        pass
```

**3. Register in Factory**:
```python
# supplier_interface.py
def create_supplier(supplier_type: SupplierType, **credentials) -> SupplierInterface:
    # ... existing cases ...
    elif supplier_type == SupplierType.ARROW:
        from .arrow_supplier import ArrowSupplier
        return ArrowSupplier(**credentials)
```

**4. Add to Implemented List**:
```python
# supplier_interface.py
IMPLEMENTED_SUPPLIERS = [
    SupplierType.JLCPCB,
    SupplierType.LCSC,
    SupplierType.DIGIKEY,
    SupplierType.MOUSER,
    SupplierType.ARROW,  # Add here
]
```

**5. Add Lazy Loading**:
```python
# __init__.py
def __getattr__(name: str):
    # ... existing cases ...
    elif name == "ArrowSupplier":
        from .arrow_supplier import ArrowSupplier
        return ArrowSupplier
```

**6. Write Tests**:
```python
# tests/test_supplier_interface.py
def test_arrow_implements_interface():
    """REQ-INTERFACE-001: Arrow implements SupplierInterface."""
    supplier = create_supplier(SupplierType.ARROW)
    assert isinstance(supplier, SupplierInterface)
    assert supplier.supplier_type == SupplierType.ARROW
```

## Performance Considerations

### Caching Strategy

**Current**: No caching (fresh data every search)

**Future**:
- In-memory cache with TTL (e.g., 5 minutes)
- Persistent cache for slow suppliers (Digikey API has rate limits)
- Cache key: `(supplier_type, mpn)` tuple

### Rate Limiting

**Scraper-Based Suppliers** (JLCPCB, LCSC):
- No official rate limits
- Respectful delays (1-2s between requests)
- User-Agent rotation to avoid blocks

**API-Based Suppliers** (Digikey, Mouser):
- Respect API rate limits (documented by supplier)
- Token bucket algorithm for request throttling
- Exponential backoff on 429 responses

### Network Timeouts

**Default**: 10 seconds per request

**Configuration**: Timeout configurable via kwargs

**Behavior on Timeout**: Return empty list, log warning, continue

## Future Enhancements

**Short Term**:
- [ ] Configurable variant preferences per supplier
- [ ] Stock-aware variant selection (prefer in-stock variants)
- [ ] Price-aware variant selection (cheapest for quantity needed)
- [ ] Search timeout handling (configurable per supplier)

**Medium Term**:
- [ ] Result caching (in-memory, configurable TTL)
- [ ] Batch search (multiple MPNs in single request)
- [ ] Additional suppliers (Arrow, Newark, Farnell)

**Long Term**:
- [ ] Offline mode with cached data
- [ ] Price history tracking
- [ ] Stock alerts (notify when part back in stock)
- [ ] Cross-supplier price comparison

## References

- `README.md` - User-facing documentation and quick start guide
- `REQUIREMENTS.md` - Numbered requirements with traceability
- `docs/` - Supplier-specific documentation (API docs, authentication guides)
