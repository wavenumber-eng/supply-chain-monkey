"""
LCSC Supplier Implementation

This module implements the SupplierInterface for LCSC (lcsc.com), which is part of the
JLC company family. LCSC uses the same C code numbering system as JLCPCB.

LCSC may provide faster response times than JLCPCB for the same parts, making it
useful for performance comparison and fallback searches.

Features:
    - Web scraping-based search (no API key required)
    - Search by manufacturer part number
    - Get details by C code (same as JLCPCB)
    - Stock availability checking
    - Part description extraction

Usage:
    >>> from supply_chain_monkey import create_supplier, SupplierType
    >>>
    >>> lcsc = create_supplier(SupplierType.LCSC)
    >>>
    >>> # Search by MPN
    >>> results = lcsc.search_by_mpn("TPS543620RPYR")
    >>> for part in results:
    ...     log.info(f"{part.supplier_part_number}: {part.stock_quantity} in stock")
    >>>
    >>> # Get specific C code details
    >>> part = lcsc.get_part_details("C2870085")
    >>> if part:
    ...     log.info(part.description)
"""


from .supplier_interface import SupplierInterface, SupplierPartInfo, SupplierType

try:
    from .lcsc_scraper import get_lcsc_part_details, search_lcsc_by_mpn
except ImportError:
    # Handle different import contexts
    from lcsc_scraper import get_lcsc_part_details, search_lcsc_by_mpn

import logging

log = logging.getLogger(__name__)



class LCSCSupplier(SupplierInterface):
    """
    LCSC implementation of the supplier interface.

    This wraps the lcsc_scraper.py functionality to provide a
    standardized interface for LCSC part searches.

    LCSC Notes:
        - Uses web scraping (no API key required)
        - Parts identified by "C codes" (same as JLCPCB: C1, C2040, C2870085, etc.)
        - Part of the JLC company family
        - May have faster response times than JLCPCB
        - Search may return multiple C codes for same MPN
        - Verification option available (slower but more accurate)

    Credentials:
        No credentials required for scraper-based implementation.
    """

    def __init__(self, **credentials):
        """
        Initialize LCSC supplier client.

        Args:
            **credentials: Currently unused (scraper doesn't need auth)
        """
        super().__init__(**credentials)

    @property
    def supplier_type(self) -> SupplierType:
        """Return LCSC supplier type."""
        return SupplierType.LCSC

    @property
    def parameter_field_name(self) -> str:
        """
        Return the Part parameter field name for LCSC.

        This is the stable downstream parameter field for LCSC.

        Returns:
            "LCSC Part #"
        """
        return "LCSC Part #"

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search LCSC for parts matching a manufacturer part number.

        This uses the web scraper to find all C codes matching the given MPN.
        LCSC may have multiple entries for the same MPN (different packaging,
        cut tape vs reel, etc.).

        Args:
            manufacturer_part_number: MPN to search for (e.g., "TPS543620RPYR")
            **kwargs: Optional parameters
                verify_parts: bool = True (verify each C code by fetching detail page)

        Returns:
            List of SupplierPartInfo objects (empty list if none found or error)

        Example:
            >>> lcsc = LCSCSupplier()
            >>> results = lcsc.search_by_mpn("TPS543620RPYR", verify_parts=True)
            >>> for part in results:
            ...     log.info(f"{part.supplier_part_number}: {part.description}")
        """
        try:
            # Extract options
            verify = kwargs.get('verify_parts', True)

            # Use existing scraper
            lcsc_results = search_lcsc_by_mpn(manufacturer_part_number, verify_parts=verify)

            # Convert to standardized format
            results = []
            for lcsc_part in lcsc_results:
                results.append(SupplierPartInfo(
                    supplier=SupplierType.LCSC,
                    supplier_part_number=lcsc_part.lcsc_code,
                    manufacturer=lcsc_part.manufacturer,
                    manufacturer_part_number=lcsc_part.mpn,
                    description=lcsc_part.description,
                    product_url=lcsc_part.url,
                    stock_quantity=lcsc_part.stock,
                    datasheet_url="",  # Not provided by scraper
                    price_breaks=[],   # Not provided by scraper
                    lifecycle_status="",  # Not provided by scraper
                    extra_data=lcsc_part.to_dict()  # Store original scraper data
                ))

            return results

        except Exception as e:
            # Log error but don't raise - return empty list for graceful degradation
            log.info(f"Error searching LCSC for {manufacturer_part_number}: {str(e)}")
            return []

    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """
        Get detailed information for a specific LCSC C code.

        This fetches the detail page for a specific C code and extracts all
        available information (description, stock, etc.).

        Args:
            supplier_part_number: LCSC C code (e.g., "C2870085")
            **kwargs: Optional parameters
                expected_mpn: str (expected MPN for validation)

        Returns:
            SupplierPartInfo object if found, None if not found or error

        Example:
            >>> lcsc = LCSCSupplier()
            >>> part = lcsc.get_part_details("C2870085")
            >>> if part:
            ...     log.info(f"Description: {part.description}")
            ...     log.info(f"Stock: {part.stock_quantity}")
        """
        try:
            # Extract options
            expected_mpn = kwargs.get('expected_mpn', '')

            # Use existing scraper
            lcsc_part = get_lcsc_part_details(supplier_part_number, expected_mpn=expected_mpn)

            if not lcsc_part:
                return None

            # Convert to standardized format
            return SupplierPartInfo(
                supplier=SupplierType.LCSC,
                supplier_part_number=lcsc_part.lcsc_code,
                manufacturer=lcsc_part.manufacturer,
                manufacturer_part_number=lcsc_part.mpn,
                description=lcsc_part.description,
                product_url=lcsc_part.url,
                stock_quantity=lcsc_part.stock,
                datasheet_url="",  # Not provided by scraper
                price_breaks=[],   # Not provided by scraper
                lifecycle_status="",  # Not provided by scraper
                extra_data=lcsc_part.to_dict()  # Store original scraper data
            )

        except Exception as e:
            # Log error but don't raise - return None for graceful degradation
            log.info(f"Error getting details for {supplier_part_number}: {str(e)}")
            return None

    def validate_credentials(self) -> bool:
        """
        Validate LCSC access.

        For scraper-based implementation, this just checks if LCSC website
        is accessible. No credentials are required.

        Returns:
            True if LCSC is accessible, False otherwise
        """
        try:
            # Try to get details for a known part (C1 is usually a common resistor)
            self.get_part_details("C1")
            # If we got any result (even None), the scraper is working
            return True
        except Exception:
            return False


# Convenience function for backwards compatibility
def search_lcsc(manufacturer_part_number: str, verify_parts: bool = True) -> list[SupplierPartInfo]:
    """
    Convenience function for quick LCSC searches.

    This provides a simple function-based interface without needing to
    instantiate the supplier class.

    Args:
        manufacturer_part_number: MPN to search for
        verify_parts: Whether to verify each C code (slower but more accurate)

    Returns:
        List of SupplierPartInfo objects

    Example:
        >>> from supply_chain_monkey.lcsc_supplier import search_lcsc
        >>> results = search_lcsc("TPS543620RPYR")
        >>> for part in results:
        ...     log.info(part.supplier_part_number)
    """
    lcsc = LCSCSupplier()
    return lcsc.search_by_mpn(manufacturer_part_number, verify_parts=verify_parts)


if __name__ == "__main__":
    # Test the LCSC supplier implementation
    log.info("=== LCSC Supplier Test ===\n")

    lcsc = LCSCSupplier()

    # Test 1: Validate credentials (check if scraper works)
    log.info("1. Validating LCSC access...")
    if lcsc.validate_credentials():
        log.info("   [OK] LCSC is accessible\n")
    else:
        log.info("   [ERROR] Cannot access LCSC\n")

    # Test 2: Search by MPN
    test_mpn = "TPS543620RPYR"
    log.info(f"2. Searching for MPN: {test_mpn}")
    results = lcsc.search_by_mpn(test_mpn)
    log.info(f"   Found {len(results)} results:")
    for part in results:
        log.info(f"   - {part.supplier_part_number}: {part.description}")
        log.info(f"     Stock: {part.stock_quantity}")
    log.info()

    # Test 3: Get specific part details
    test_c_code = "C2870085"
    log.info(f"3. Getting details for C code: {test_c_code}")
    part = lcsc.get_part_details(test_c_code)
    if part:
        log.info(f"   Supplier Part #: {part.supplier_part_number}")
        log.info(f"   MPN: {part.manufacturer_part_number}")
        log.info(f"   Description: {part.description}")
        log.info(f"   Stock: {part.stock_quantity}")
        log.info(f"   URL: {part.product_url}")
    else:
        log.info("   [ERROR] Part not found")
    log.info()

    # Test 4: Verify parameter field name
    log.info(f"4. Parameter field name: {lcsc.parameter_field_name}")
    log.info("   (This should stay stable for downstream consumers)")
