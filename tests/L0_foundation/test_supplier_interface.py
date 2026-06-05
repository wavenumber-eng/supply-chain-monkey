"""
Tests for supplier interface module.

Tests all supplier implementations (JLCPCB, Digikey, etc.) to ensure:
1. They can search for parts correctly
2. They return expected part numbers
3. They return valid data (stock, description, etc.)
4. Performance is acceptable

⚠️ IMPORTANT: RATE LIMITING WARNING ⚠️
These tests make REAL network requests to supplier APIs/websites!
- Running tests frequently may trigger rate limiting or IP blocks
- Each test performs actual searches against live supplier databases
- BE RESPECTFUL of supplier terms of service
- Only run tests when modifying supplier code or validating changes
- DO NOT run in automated loops or on every commit

These tests require internet connectivity and valid API credentials.
"""

import os
import time

import pytest

from scm.models import SupplierType
from scm.server.providers.base import (
    SupplierPartInfo,
    create_supplier,
    get_available_suppliers,
)

LIVE_SUPPLIER_TESTS_ENABLED = os.getenv("SUPPLY_CHAIN_ENABLE_LIVE_TESTS", "0") == "1"

pytestmark = pytest.mark.skipif(
    not LIVE_SUPPLIER_TESTS_ENABLED,
    reason="Live supplier tests disabled (set SUPPLY_CHAIN_ENABLE_LIVE_TESTS=1 and configure .env)",
)

# ============================================================================
# Pytest Fixtures
# ============================================================================

# Test part to search for across all suppliers
TEST_MPN = "TPS543620RPYR"

# Expected results for each supplier
EXPECTED_RESULTS = {
    SupplierType.JLCPCB: {
        "part_number": "C2870085",
        "requires_credentials": False,
        "manufacturer": "Texas Instruments",  # TI or Texas Instruments
    },
    SupplierType.LCSC: {
        "part_number": "C2870085",  # Same C code as JLCPCB (same company family)
        "requires_credentials": False,
        "manufacturer": "Texas Instruments",  # TI or Texas Instruments
    },
    SupplierType.DIGIKEY: {
        "part_number_contains": "296-TPS543620RPYR",  # Could be CT-ND, TR-ND, etc.
        "part_number_suffix": "-ND",  # Digikey part numbers end in -ND
        "requires_credentials": True,
        "manufacturer": "Texas Instruments",
    },
    SupplierType.MOUSER: {
        "part_number_contains": "595-TPS543620RPYR",  # Mouser part numbers have prefix
        "requires_credentials": True,
        "manufacturer": "Texas Instruments",
    }
}

# Performance thresholds (in seconds)
PERFORMANCE_THRESHOLDS = {
    SupplierType.JLCPCB: 10.0,  # JLCPCB scraper should be fast
    SupplierType.LCSC: 10.0,     # LCSC scraper (comparing performance with JLCPCB)
    SupplierType.DIGIKEY: 5.0,   # Digikey API should be very fast
    SupplierType.MOUSER: 5.0,    # Mouser API should be very fast
}


# ============================================================================
# Helper Functions
# ============================================================================

def has_credentials_for_supplier(supplier_type: SupplierType) -> bool:
    """Check if credentials are available for a supplier."""
    if supplier_type == SupplierType.JLCPCB:
        return True  # Search is scraper-backed; detail can also use official API when configured.

    elif supplier_type == SupplierType.LCSC:
        return True  # LCSC doesn't require credentials (uses scraping)

    elif supplier_type == SupplierType.DIGIKEY:
        # Check for Digikey credentials in environment
        return bool(os.getenv('DIGIKEY_CLIENT_ID') and os.getenv('DIGIKEY_CLIENT_SECRET'))

    elif supplier_type == SupplierType.MOUSER:
        return bool(os.getenv('MOUSER_API_KEY'))

    return False


def validate_supplier_part_info(part_info: SupplierPartInfo, supplier_type: SupplierType, check_manufacturer: bool = True):
    """
    Validate that a SupplierPartInfo object has all required fields.

    Args:
        part_info: SupplierPartInfo object to validate
        supplier_type: Type of supplier (for specific validation)
        check_manufacturer: If True, validate manufacturer field is present

    Raises:
        AssertionError: If validation fails
    """
    # Required fields
    assert part_info.supplier == supplier_type, f"Supplier mismatch: expected {supplier_type}, got {part_info.supplier}"
    assert part_info.supplier_part_number, "Missing supplier_part_number"
    assert part_info.manufacturer_part_number, "Missing manufacturer_part_number"

    # Highly recommended fields
    assert part_info.description, "Missing description"

    # Manufacturer field (added in recent update)
    if check_manufacturer:
        assert part_info.manufacturer, "Missing manufacturer (should be extracted from detail page)"
        # Check manufacturer matches expected (normalized comparison)
        if supplier_type in EXPECTED_RESULTS:
            expected_mfr = EXPECTED_RESULTS[supplier_type].get("manufacturer", "")
            if expected_mfr:
                # Normalize both (case-insensitive, handle "TI" vs "Texas Instruments")
                actual_norm = part_info.manufacturer.upper()
                expected_norm = expected_mfr.upper()
                # Accept if either contains the other (handles "TI" in "Texas Instruments")
                assert expected_norm in actual_norm or actual_norm in expected_norm or actual_norm == "TI", \
                    f"Manufacturer mismatch: expected '{expected_mfr}', got '{part_info.manufacturer}'"

    # Stock should be an integer >= 0
    assert isinstance(part_info.stock_quantity, int), f"Stock should be int, got {type(part_info.stock_quantity)}"
    assert part_info.stock_quantity >= 0, f"Stock should be >= 0, got {part_info.stock_quantity}"


def ascii_preview(value: str | None, limit: int = 80) -> str:
    """Return an ASCII-safe preview for live supplier debug output."""
    return (value or "")[:limit].encode("ascii", "replace").decode("ascii")


# ============================================================================
# Import Tests
# ============================================================================

def test_supplier_interface_imports():
    """Test that supplier interface module can be imported without errors."""
    from scm.server.providers import (
        SupplierInterface,
        SupplierPartInfo,
        SupplierType,
        create_supplier,
        get_available_suppliers,
    )

    assert SupplierType is not None
    assert SupplierPartInfo is not None
    assert SupplierInterface is not None
    assert create_supplier is not None
    assert get_available_suppliers is not None


def test_supplier_implementations_importable():
    """Test that all supplier implementations can be imported."""
    from scm.server.providers.digikey import DigikeySupplier
    from scm.server.providers.jlc import JLCPCBSupplier
    from scm.server.providers.lcsc import LCSCSupplier
    from scm.server.providers.mouser import MouserSupplier

    assert JLCPCBSupplier is not None
    assert LCSCSupplier is not None
    assert DigikeySupplier is not None
    assert MouserSupplier is not None


# ============================================================================
# Factory Tests
# ============================================================================

def test_create_jlcpcb_supplier():
    """Test creating JLCPCB supplier instance."""
    supplier = create_supplier(SupplierType.JLCPCB)
    assert supplier is not None
    assert supplier.supplier_type == SupplierType.JLCPCB
    assert supplier.parameter_field_name == "JLCPCB Part #"


def test_create_jlcpcb_supplier_legacy_detail_backend():
    """Test creating JLCPCB supplier with explicit legacy scraper detail mode."""
    from scm.server.providers.jlc import JLCPCBSupplier

    supplier = create_supplier(SupplierType.JLCPCB, detail_backend="legacy_scraper")
    assert supplier is not None
    assert isinstance(supplier, JLCPCBSupplier)
    assert supplier.supplier_type == SupplierType.JLCPCB
    assert supplier.parameter_field_name == "JLCPCB Part #"
    assert supplier.detail_backend == "legacy_scraper"


def test_create_lcsc_supplier():
    """Test creating LCSC supplier instance."""
    supplier = create_supplier(SupplierType.LCSC)
    assert supplier is not None
    assert supplier.supplier_type == SupplierType.LCSC
    assert supplier.parameter_field_name == "LCSC Part #"


@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.DIGIKEY),
    reason="Digikey credentials not available"
)
def test_create_digikey_supplier():
    """Test creating Digikey supplier instance."""
    supplier = create_supplier(SupplierType.DIGIKEY)
    assert supplier is not None
    assert supplier.supplier_type == SupplierType.DIGIKEY
    assert supplier.parameter_field_name == "Digikey Part #"


@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.MOUSER),
    reason="Mouser credentials not available"
)
def test_create_mouser_supplier():
    """Test creating Mouser supplier instance."""
    supplier = create_supplier(SupplierType.MOUSER)
    assert supplier is not None
    assert supplier.supplier_type == SupplierType.MOUSER
    assert supplier.parameter_field_name == "Mouser Part #"


# ============================================================================
# JLCPCB Search Tests
# ============================================================================

@pytest.mark.supplier
@pytest.mark.slow
def test_jlcpcb_search_by_mpn():
    """
    Test JLCPCB search for TPS543620RPYR.
    Should return C2870085.
    """
    # Create supplier
    supplier = create_supplier(SupplierType.JLCPCB)

    # Time the search
    start_time = time.time()
    results = supplier.search_by_mpn(TEST_MPN, verify_parts=True)
    elapsed_time = time.time() - start_time

    # Print timing info
    print(f"\n[JLCPCB] Search completed in {elapsed_time:.2f}s")

    # Check performance
    threshold = PERFORMANCE_THRESHOLDS[SupplierType.JLCPCB]
    assert elapsed_time < threshold, f"JLCPCB search took {elapsed_time:.2f}s (threshold: {threshold}s)"

    # Should have at least one result
    assert len(results) > 0, f"JLCPCB search for {TEST_MPN} returned no results"

    # Check if expected part number is in results
    expected_part = EXPECTED_RESULTS[SupplierType.JLCPCB]["part_number"]
    part_numbers = [r.supplier_part_number for r in results]

    print(f"[JLCPCB] Found {len(results)} result(s): {', '.join(part_numbers)}")

    assert expected_part in part_numbers, \
        f"Expected part {expected_part} not found in results: {part_numbers}"

    # Validate the expected part
    matching_part = next(r for r in results if r.supplier_part_number == expected_part)
    validate_supplier_part_info(matching_part, SupplierType.JLCPCB)

    print(f"[JLCPCB] Part {expected_part}:")
    print(f"  MPN: {matching_part.manufacturer_part_number}")
    # Handle Unicode characters in description
    desc = ascii_preview(matching_part.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {matching_part.stock_quantity}")


@pytest.mark.supplier
def test_jlcpcb_get_part_details():
    """Test JLCPCB get_part_details for C2870085 using the default hybrid detail path."""
    supplier = create_supplier(SupplierType.JLCPCB)

    expected_part = EXPECTED_RESULTS[SupplierType.JLCPCB]["part_number"]

    # Time the request
    start_time = time.time()
    result = supplier.get_part_details(expected_part, expected_mpn=TEST_MPN)
    elapsed_time = time.time() - start_time

    print(f"\n[JLCPCB] Part details fetched in {elapsed_time:.2f}s")

    # Should return a result
    assert result is not None, f"JLCPCB get_part_details for {expected_part} returned None"

    # Validate result
    validate_supplier_part_info(result, SupplierType.JLCPCB)

    # Check part number matches
    assert result.supplier_part_number == expected_part
    assert result.extra_data.get("detail_backend") == "hybrid"

    print(f"[JLCPCB] Part details for {expected_part}:")
    print(f"  MPN: {result.manufacturer_part_number}")
    desc = ascii_preview(result.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {result.stock_quantity}")


@pytest.mark.supplier
def test_jlcpcb_get_part_details_api_only():
    """Test JLCPCB get_part_details for C2870085 using the official API-only path."""
    supplier = create_supplier(SupplierType.JLCPCB, detail_backend="api")

    expected_part = EXPECTED_RESULTS[SupplierType.JLCPCB]["part_number"]

    start_time = time.time()
    result = supplier.get_part_details(expected_part, expected_mpn=TEST_MPN)
    elapsed_time = time.time() - start_time

    print(f"\n[JLCPCB api] Part details fetched in {elapsed_time:.2f}s")

    assert result is not None, f"JLCPCB API get_part_details for {expected_part} returned None"
    validate_supplier_part_info(result, SupplierType.JLCPCB, check_manufacturer=False)
    assert result.supplier_part_number == expected_part
    assert result.extra_data.get("detail_backend") == "api"
    assert result.price_breaks, "Expected price breaks from official JLC API detail response"
    assert result.datasheet_url, "Expected datasheet URL from official JLC API detail response"


@pytest.mark.supplier
def test_jlcpcb_get_part_details_legacy_scraper():
    """Test JLCPCB get_part_details for C2870085 using the explicit legacy scraper path."""
    supplier = create_supplier(SupplierType.JLCPCB, detail_backend="legacy_scraper")

    expected_part = EXPECTED_RESULTS[SupplierType.JLCPCB]["part_number"]

    start_time = time.time()
    result = supplier.get_part_details(expected_part, expected_mpn=TEST_MPN)
    elapsed_time = time.time() - start_time

    print(f"\n[JLCPCB legacy] Part details fetched in {elapsed_time:.2f}s")

    assert result is not None, f"JLCPCB legacy get_part_details for {expected_part} returned None"
    validate_supplier_part_info(result, SupplierType.JLCPCB)
    assert result.supplier_part_number == expected_part
    assert result.extra_data.get("detail_backend") == "legacy_scraper"


# ============================================================================
# LCSC Search Tests (Performance Comparison with JLCPCB)
# ============================================================================

@pytest.mark.supplier
@pytest.mark.slow
def test_lcsc_search_by_mpn():
    """
    Test LCSC search for TPS543620RPYR.
    Should return C2870085 (same as JLCPCB - they're the same company family).
    This test is used for performance comparison with JLCPCB.
    """
    # Create supplier
    supplier = create_supplier(SupplierType.LCSC)

    # Time the search
    start_time = time.time()
    results = supplier.search_by_mpn(TEST_MPN, verify_parts=True)
    elapsed_time = time.time() - start_time

    # Print timing info
    print(f"\n[LCSC] Search completed in {elapsed_time:.2f}s")

    # Check performance
    threshold = PERFORMANCE_THRESHOLDS[SupplierType.LCSC]
    assert elapsed_time < threshold, f"LCSC search took {elapsed_time:.2f}s (threshold: {threshold}s)"

    # Should have at least one result
    assert len(results) > 0, f"LCSC search for {TEST_MPN} returned no results"

    # Check if expected part number is in results
    expected_part = EXPECTED_RESULTS[SupplierType.LCSC]["part_number"]
    part_numbers = [r.supplier_part_number for r in results]

    print(f"[LCSC] Found {len(results)} result(s): {', '.join(part_numbers)}")

    assert expected_part in part_numbers, \
        f"Expected part {expected_part} not found in results: {part_numbers}"

    # Validate the expected part
    matching_part = next(r for r in results if r.supplier_part_number == expected_part)
    validate_supplier_part_info(matching_part, SupplierType.LCSC)

    print(f"[LCSC] Part {expected_part}:")
    print(f"  MPN: {matching_part.manufacturer_part_number}")
    # Handle Unicode characters in description
    desc = ascii_preview(matching_part.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {matching_part.stock_quantity}")


@pytest.mark.supplier
def test_lcsc_get_part_details():
    """Test LCSC get_part_details for C2870085."""
    supplier = create_supplier(SupplierType.LCSC)

    expected_part = EXPECTED_RESULTS[SupplierType.LCSC]["part_number"]

    # Time the request
    start_time = time.time()
    result = supplier.get_part_details(expected_part, expected_mpn=TEST_MPN)
    elapsed_time = time.time() - start_time

    print(f"\n[LCSC] Part details fetched in {elapsed_time:.2f}s")

    # Should return a result
    assert result is not None, f"LCSC get_part_details for {expected_part} returned None"

    # Validate result
    validate_supplier_part_info(result, SupplierType.LCSC)

    # Check part number matches
    assert result.supplier_part_number == expected_part

    print(f"[LCSC] Part details for {expected_part}:")
    print(f"  MPN: {result.manufacturer_part_number}")
    desc = ascii_preview(result.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {result.stock_quantity}")


# ============================================================================
# Digikey Search Tests
# ============================================================================

@pytest.mark.supplier
@pytest.mark.slow
@pytest.mark.requires_credentials
@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.DIGIKEY),
    reason="Digikey credentials not available (set DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET)"
)
def test_digikey_search_by_mpn():
    """
    Test Digikey search for TPS543620RPYR.
    Should return part number containing "296-TPS543620RPYR" and ending in "-ND".
    Common variants: CT-ND (cut tape), TR-ND (tape and reel), DKR-ND (digi-reel).
    """
    # Create supplier
    supplier = create_supplier(SupplierType.DIGIKEY)

    # Time the search
    start_time = time.time()
    results = supplier.search_by_mpn(TEST_MPN)
    elapsed_time = time.time() - start_time

    # Print timing info
    print(f"\n[Digikey] Search completed in {elapsed_time:.2f}s")

    # Check performance
    threshold = PERFORMANCE_THRESHOLDS[SupplierType.DIGIKEY]
    assert elapsed_time < threshold, f"Digikey search took {elapsed_time:.2f}s (threshold: {threshold}s)"

    # Should have at least one result
    assert len(results) > 0, f"Digikey search for {TEST_MPN} returned no results"

    # Check for expected part number pattern
    expected_contains = EXPECTED_RESULTS[SupplierType.DIGIKEY]["part_number_contains"]
    expected_suffix = EXPECTED_RESULTS[SupplierType.DIGIKEY]["part_number_suffix"]

    part_numbers = [r.supplier_part_number for r in results]
    print(f"[Digikey] Found {len(results)} result(s): {', '.join(part_numbers[:5])}")

    # Find parts matching the expected pattern
    matching_parts = [
        r for r in results
        if expected_contains in r.supplier_part_number and
           r.supplier_part_number.endswith(expected_suffix)
    ]

    assert len(matching_parts) > 0, \
        f"No Digikey parts found matching pattern '{expected_contains}*{expected_suffix}' in results: {part_numbers}"

    # Validate the first matching part
    matching_part = matching_parts[0]
    validate_supplier_part_info(matching_part, SupplierType.DIGIKEY)

    print(f"[Digikey] Part {matching_part.supplier_part_number}:")
    print(f"  MPN: {matching_part.manufacturer_part_number}")
    print(f"  Manufacturer: {matching_part.manufacturer}")
    desc = ascii_preview(matching_part.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {matching_part.stock_quantity}")
    print(f"  Lifecycle: {matching_part.lifecycle_status}")

    # Digikey should provide additional info
    if matching_part.datasheet_url:
        print(f"  Datasheet: {matching_part.datasheet_url}")
    if matching_part.price_breaks:
        print(f"  Pricing: {len(matching_part.price_breaks)} price break(s)")


@pytest.mark.supplier
@pytest.mark.requires_credentials
@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.DIGIKEY),
    reason="Digikey credentials not available (set DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET)"
)
@pytest.mark.xfail(reason="Digikey get_part_details not populating supplier_part_number - API integration issue")
def test_digikey_get_part_details():
    """Test Digikey get_part_details for a specific Digikey part number."""
    supplier = create_supplier(SupplierType.DIGIKEY)

    # First search to find a valid part number
    search_results = supplier.search_by_mpn(TEST_MPN)
    assert len(search_results) > 0, "No search results to test get_part_details"

    # Find the first result with a non-empty supplier_part_number
    test_part_number = None
    for result in search_results:
        if result.supplier_part_number:
            test_part_number = result.supplier_part_number
            break

    assert test_part_number, "No search results with valid supplier_part_number"

    # Time the request
    start_time = time.time()
    result = supplier.get_part_details(test_part_number, expected_mpn=TEST_MPN)
    elapsed_time = time.time() - start_time

    print(f"\n[Digikey] Part details fetched in {elapsed_time:.2f}s")

    # Should return a result
    assert result is not None, f"Digikey get_part_details for {test_part_number} returned None"

    # Validate result
    validate_supplier_part_info(result, SupplierType.DIGIKEY)

    # Check part number matches
    assert result.supplier_part_number == test_part_number

    print(f"[Digikey] Part details for {test_part_number}:")
    print(f"  MPN: {result.manufacturer_part_number}")
    print(f"  Manufacturer: {result.manufacturer}")
    desc = ascii_preview(result.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {result.stock_quantity}")


# ============================================================================
# Mouser Search Tests
# ============================================================================

@pytest.mark.supplier
@pytest.mark.slow
@pytest.mark.requires_credentials
@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.MOUSER),
    reason="Mouser credentials not available (set MOUSER_API_KEY)"
)
def test_mouser_search_by_mpn():
    """
    Test Mouser search for TPS543620RPYR.
    Should return part number containing "595-TPS543620RPYR".
    """
    # Create supplier
    supplier = create_supplier(SupplierType.MOUSER)

    # Time the search
    start_time = time.time()
    results = supplier.search_by_mpn(TEST_MPN)
    elapsed_time = time.time() - start_time

    # Print timing info
    print(f"\n[Mouser] Search completed in {elapsed_time:.2f}s")

    # Check performance
    threshold = PERFORMANCE_THRESHOLDS[SupplierType.MOUSER]
    assert elapsed_time < threshold, f"Mouser search took {elapsed_time:.2f}s (threshold: {threshold}s)"

    # Should have at least one result
    assert len(results) > 0, f"Mouser search for {TEST_MPN} returned no results"

    # Check for expected part number pattern
    expected_contains = EXPECTED_RESULTS[SupplierType.MOUSER]["part_number_contains"]

    part_numbers = [r.supplier_part_number for r in results]
    print(f"[Mouser] Found {len(results)} result(s): {', '.join(part_numbers[:5])}")

    # Find parts matching the expected pattern
    matching_parts = [
        r for r in results
        if expected_contains in r.supplier_part_number
    ]

    assert len(matching_parts) > 0, \
        f"No Mouser parts found matching pattern '{expected_contains}' in results: {part_numbers}"

    # Validate the first matching part
    matching_part = matching_parts[0]
    validate_supplier_part_info(matching_part, SupplierType.MOUSER)

    print(f"[Mouser] Part {matching_part.supplier_part_number}:")
    print(f"  MPN: {matching_part.manufacturer_part_number}")
    print(f"  Manufacturer: {matching_part.manufacturer}")
    desc = ascii_preview(matching_part.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {matching_part.stock_quantity}")
    print(f"  Lifecycle: {matching_part.lifecycle_status}")

    # Mouser should provide additional info
    if matching_part.datasheet_url:
        print(f"  Datasheet: {matching_part.datasheet_url}")
    if matching_part.price_breaks:
        print(f"  Pricing: {len(matching_part.price_breaks)} price break(s)")
        print(f"  Price (1pc): ${matching_part.price_breaks[0].get('unit_price', 0.0):.4f}")


@pytest.mark.supplier
@pytest.mark.requires_credentials
@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.MOUSER),
    reason="Mouser credentials not available (set MOUSER_API_KEY)"
)
def test_mouser_get_part_details():
    """Test Mouser get_part_details for a specific Mouser part number."""
    supplier = create_supplier(SupplierType.MOUSER)

    # First search to find a valid part number
    search_results = supplier.search_by_mpn(TEST_MPN)
    assert len(search_results) > 0, "No search results to test get_part_details"

    # Use the first result's part number
    test_part_number = search_results[0].supplier_part_number

    # Time the request
    start_time = time.time()
    result = supplier.get_part_details(test_part_number)
    elapsed_time = time.time() - start_time

    print(f"\n[Mouser] Part details fetched in {elapsed_time:.2f}s")

    # Should return a result
    assert result is not None, f"Mouser get_part_details for {test_part_number} returned None"

    # Validate result
    validate_supplier_part_info(result, SupplierType.MOUSER)

    # Check part number matches
    assert result.supplier_part_number == test_part_number

    print(f"[Mouser] Part details for {test_part_number}:")
    print(f"  MPN: {result.manufacturer_part_number}")
    print(f"  Manufacturer: {result.manufacturer}")
    desc = ascii_preview(result.description)
    print(f"  Description: {desc}")
    print(f"  Stock: {result.stock_quantity}")


# ============================================================================
# Multi-Supplier Tests
# ============================================================================

@pytest.mark.supplier
@pytest.mark.slow
def test_search_all_available_suppliers():
    """
    Test searching across all available suppliers.
    This demonstrates how to implement multi-supplier search.
    """
    print(f"\n[Multi-Supplier] Searching for {TEST_MPN} across all suppliers...")

    all_results = []
    timings = {}

    for supplier_type in get_available_suppliers():
        # Skip if credentials not available
        if not has_credentials_for_supplier(supplier_type):
            print(f"[{supplier_type.value}] Skipping (no credentials)")
            continue

        try:
            # Create supplier
            supplier = create_supplier(supplier_type)

            # Time the search
            start_time = time.time()
            results = supplier.search_by_mpn(TEST_MPN)
            elapsed_time = time.time() - start_time

            timings[supplier_type.value] = elapsed_time

            print(f"[{supplier_type.value}] Found {len(results)} result(s) in {elapsed_time:.2f}s")

            # Validate results
            for result in results:
                validate_supplier_part_info(result, supplier_type)

            all_results.extend(results)

        except Exception as e:
            print(f"[{supplier_type.value}] Error: {str(e)}")

    # Should have results from at least one supplier
    assert len(all_results) > 0, "No results from any supplier"

    # Print summary
    print(f"\n[Summary] Total results: {len(all_results)} from {len(timings)} supplier(s)")
    print("Timing breakdown:")
    for supplier, elapsed in sorted(timings.items(), key=lambda x: x[1]):
        print(f"  {supplier}: {elapsed:.2f}s")


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_jlcpcb_nonexistent_part():
    """Test JLCPCB search with a part that doesn't exist."""
    supplier = create_supplier(SupplierType.JLCPCB)

    # Search for a nonsense part number
    results = supplier.search_by_mpn("NONEXISTENT_PART_12345_XYZ", verify_parts=False)

    # Should return empty list, not raise an error
    assert isinstance(results, list)
    assert len(results) == 0


def test_jlcpcb_invalid_c_code():
    """Test JLCPCB get_part_details with invalid C code."""
    supplier = create_supplier(SupplierType.JLCPCB)

    # Try to get details for a nonsense C code
    result = supplier.get_part_details("C999999999")

    # Should return a result or None - either is valid (scraper extracts what it can)
    # The important thing is it doesn't raise an error
    assert result is None or isinstance(result, SupplierPartInfo)


@pytest.mark.skipif(
    not has_credentials_for_supplier(SupplierType.DIGIKEY),
    reason="Digikey credentials not available"
)
def test_digikey_nonexistent_part():
    """Test Digikey search with a part that doesn't exist."""
    supplier = create_supplier(SupplierType.DIGIKEY)

    # Search for a nonsense part number
    results = supplier.search_by_mpn("NONEXISTENT_PART_12345_XYZ")

    # Should return empty list, not raise an error
    assert isinstance(results, list)
    assert len(results) == 0


# ============================================================================
# Performance Benchmark
# ============================================================================

@pytest.mark.supplier
@pytest.mark.benchmark
@pytest.mark.slow
def test_supplier_search_performance_benchmark():
    """
    Benchmark test for supplier search performance.
    Run with: pytest -v -m benchmark

    NOTE: Only runs ONE search per supplier to avoid rate limiting!
    """
    print("\n" + "=" * 80)
    print("SUPPLIER SEARCH PERFORMANCE BENCHMARK")
    print("=" * 80)

    results_summary = []

    for supplier_type in get_available_suppliers():
        if not has_credentials_for_supplier(supplier_type):
            continue

        try:
            supplier = create_supplier(supplier_type)

            # Single search run to avoid rate limiting / getting blocked
            start_time = time.time()
            results = supplier.search_by_mpn(TEST_MPN)
            elapsed_time = time.time() - start_time

            results_summary.append({
                'supplier': supplier_type.value,
                'time': elapsed_time,
                'num_results': len(results),
                'threshold': PERFORMANCE_THRESHOLDS.get(supplier_type, 999)
            })

        except Exception as e:
            print(f"[{supplier_type.value}] Benchmark failed: {str(e)}")

    # Print results table
    print(f"\n{'Supplier':<15} {'Time':<12} {'Results':<10} {'Threshold':<12} {'Status':<10}")
    print("-" * 80)

    for result in results_summary:
        status = "PASS" if result['time'] < result['threshold'] else "SLOW"
        print(f"{result['supplier']:<15} {result['time']:>10.2f}s  {result['num_results']:>8}  "
              f"{result['threshold']:>10.2f}s  {status:<10}")

    print("=" * 80)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
