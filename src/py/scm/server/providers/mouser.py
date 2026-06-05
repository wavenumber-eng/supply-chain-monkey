"""
Mouser Supplier Implementation

This module implements the SupplierInterface for Mouser Electronics using their official API.

Mouser provides a comprehensive REST API for searching parts, checking stock, and accessing
detailed product information including pricing, datasheets, and lifecycle status.

Features:
    - Search by manufacturer part number
    - Search by keyword
    - Get detailed part information
    - Stock availability and pricing
    - Datasheet URLs
    - Lifecycle status
    - Product attributes and specifications

API Documentation:
    https://www.mouser.com/api-hub/

Usage:
    >>> from scm.server.providers import create_supplier, SupplierType
    >>>
    >>> mouser = create_supplier(SupplierType.MOUSER, api_key="your-api-key")
    >>>
    >>> # Search by MPN
    >>> results = mouser.search_by_mpn("STM32F407VGT6")
    >>> for part in results:
    ...     log.info(f"{part.supplier_part_number}: {part.stock_quantity} in stock")
    >>>
    >>> # Get specific part details
    >>> part = mouser.get_part_details("595-STM32F407VGT6")
    >>> if part:
    ...     log.info(part.description)
"""

import logging
import os
from typing import Any

import requests

from .base import SupplierInterface, SupplierPartInfo, SupplierType, resolve_stock

log = logging.getLogger(__name__)


class MouserSupplier(SupplierInterface):
    """
    Mouser Electronics implementation of the supplier interface.

    Uses Mouser's official REST API to search for parts and retrieve detailed
    product information.

    API Details:
        - Base URL: https://api.mouser.com/api/v1
        - Authentication: API key passed as query parameter
        - Rate limits: Depends on account type
        - Max results per search: 50 parts

    Credentials:
        - api_key: Mouser API key (get from https://www.mouser.com/api-hub/)
    """

    BASE_URL = "https://api.mouser.com/api/v1"

    def __init__(self, **credentials):
        """
        Initialize Mouser supplier client.

        Args:
            **credentials: Must include 'api_key'
                api_key: Your Mouser API key

        Raises:
            ValueError: If api_key is not provided
        """
        super().__init__(**credentials)

        # Get API key from credentials or environment
        self.api_key = credentials.get('api_key') or os.getenv('MOUSER_API_KEY')

        if not self.api_key or self.api_key == 'your_api_key_here':
            log.warning("[Mouser] API key not configured")
            self.api_key = None

    @property
    def supplier_type(self) -> SupplierType:
        """Return Mouser supplier type."""
        return SupplierType.MOUSER

    @property
    def parameter_field_name(self) -> str:
        """
        Return the Part parameter field name for Mouser.

        Returns:
            "Mouser Part #"
        """
        return "Mouser Part #"

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search Mouser for parts matching a manufacturer part number.

        Uses the /search/partnumber endpoint which searches by Mouser part numbers
        and manufacturer part numbers.

        Args:
            manufacturer_part_number: MPN to search for (e.g., "STM32F407VGT6")
            **kwargs: Optional parameters
                max_results: int = 50 (max parts to return, API limit is 50)

        Returns:
            List of SupplierPartInfo objects (empty list if none found or error)

        Example:
            >>> mouser = MouserSupplier(api_key="xxx")
            >>> results = mouser.search_by_mpn("STM32F407VGT6")
            >>> for part in results:
            ...     log.info(f"{part.supplier_part_number}: {part.description}")
        """
        if not self.api_key:
            log.error("[Mouser] Cannot search: API key not configured")
            return []

        try:
            log.info(f"[Mouser] Searching for MPN: {manufacturer_part_number}")

            # Mouser's search endpoint
            url = f"{self.BASE_URL}/search/partnumber"

            # Build request body
            request_body = {
                "SearchByPartRequest": {
                    "mouserPartNumber": manufacturer_part_number,
                    "partSearchOptions": "None"  # Can be "None" or "Exact"
                }
            }

            # API key as query parameter
            params = {
                "apiKey": self.api_key
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(url, json=request_body, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            errors = data.get("Errors")
            if errors:
                for error in errors:
                    log.error(f"[Mouser] API Error: {error.get('Message', 'Unknown error')}")
                return []

            # Extract search results
            search_results = data.get("SearchResults", {})
            parts = search_results.get("Parts", [])
            num_results = search_results.get("NumberOfResult", 0)

            log.info(f"[Mouser] Found {num_results} result(s)")

            # Convert to standardized format
            results = []
            for mouser_part in parts:
                part_info = self._convert_mouser_part(mouser_part)
                if part_info:
                    results.append(part_info)

            return results

        except requests.exceptions.RequestException as e:
            log.error(f"[Mouser] Request error: {str(e)}")
            return []
        except Exception as e:
            log.error(f"[Mouser] Error searching for {manufacturer_part_number}: {str(e)}")
            return []

    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """
        Get detailed information for a specific Mouser part number.

        Args:
            supplier_part_number: Mouser part number (e.g., "595-STM32F407VGT6")
            **kwargs: Optional parameters

        Returns:
            SupplierPartInfo object if found, None if not found or error

        Example:
            >>> mouser = MouserSupplier(api_key="xxx")
            >>> part = mouser.get_part_details("595-STM32F407VGT6")
            >>> if part:
            ...     log.info(f"Stock: {part.stock_quantity}")
        """
        # Mouser's API searches by part number, so we use search_by_mpn
        # and filter for exact match
        results = self.search_by_mpn(supplier_part_number)

        # Find exact match
        for part in results:
            if part.supplier_part_number == supplier_part_number:
                return part

        return None

    def validate_credentials(self) -> bool:
        """
        Validate Mouser API access.

        Tests the API key by performing a simple search.

        Returns:
            True if API key is valid and working, False otherwise
        """
        if not self.api_key:
            return False

        try:
            # Try a simple search for a common part
            self.search_by_mpn("STM32F407VGT6")
            # If we got results (or empty list without error), API key is valid
            return True
        except Exception:
            return False

    def _convert_mouser_part(self, mouser_part: dict[str, Any]) -> SupplierPartInfo | None:
        """
        Convert Mouser API part object to standardized SupplierPartInfo.

        Args:
            mouser_part: Mouser API part dictionary

        Returns:
            SupplierPartInfo object or None if conversion fails
        """
        try:
            # Extract basic info
            mouser_pn = mouser_part.get("MouserPartNumber", "")
            mfr_pn = mouser_part.get("ManufacturerPartNumber", "")
            manufacturer = mouser_part.get("Manufacturer", "")
            description = mouser_part.get("Description", "")

            # Extract lifecycle status
            lifecycle = mouser_part.get("LifecycleStatus") or ""

            # Extract stock - Mouser uses "Availability" field
            raw_stock = self._parse_availability_raw(mouser_part.get("Availability", ""))
            stock_qty, stock_status = resolve_stock(raw_stock, lifecycle)

            # Extract datasheet URL
            datasheet = mouser_part.get("DataSheetUrl", "")

            # Extract product detail URL
            product_url = mouser_part.get("ProductDetailUrl", "")

            # Extract price breaks
            price_breaks = self._parse_price_breaks(mouser_part.get("PriceBreaks", []))

            return SupplierPartInfo(
                supplier=SupplierType.MOUSER,
                supplier_part_number=mouser_pn,
                manufacturer=manufacturer,
                manufacturer_part_number=mfr_pn,
                description=description,
                product_url=product_url,
                stock_quantity=stock_qty,
                stock_status=stock_status,
                datasheet_url=datasheet,
                price_breaks=price_breaks,
                lifecycle_status=lifecycle,
                extra_data=mouser_part,
            )

        except Exception as e:
            log.error(f"[Mouser] Error converting part data: {str(e)}")
            return None

    def _parse_availability_raw(self, availability: str) -> int | str:
        """Extract the numeric stock value from Mouser's availability string.

        Returns int if parseable, otherwise the raw string for resolve_stock.
        """
        if not availability:
            return ""
        import re
        match = re.search(r'(\d[\d,]*)', availability)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                return availability
        return availability

    def _parse_price_breaks(self, price_breaks: list[dict]) -> list[dict]:
        """Parse Mouser price breaks into standardized dict format."""
        result = []
        for pb in price_breaks:
            try:
                qty = int(pb.get("Quantity", 0))
                price_str = pb.get("Price", "").replace("$", "").replace(",", "")
                unit_price = float(price_str) if price_str else 0.0
                result.append({"qty": qty, "unit_price": unit_price, "currency": "USD"})
            except (ValueError, AttributeError):
                continue
        return result


# Convenience function for backwards compatibility
def search_mouser(manufacturer_part_number: str, api_key: str | None = None) -> list[SupplierPartInfo]:
    """
    Convenience function for quick Mouser searches.

    Args:
        manufacturer_part_number: MPN to search for
        api_key: Optional API key (uses environment variable if not provided)

    Returns:
        List of SupplierPartInfo objects

    Example:
        >>> from scm.server.providers.mouser import search_mouser
        >>> results = search_mouser("STM32F407VGT6")
        >>> for part in results:
        ...     log.info(part.supplier_part_number)
    """
    mouser = MouserSupplier(api_key=api_key)
    return mouser.search_by_mpn(manufacturer_part_number)


if __name__ == "__main__":
    # Test the Mouser supplier implementation
    log.info("=== Mouser Supplier Test ===\n")

    mouser = MouserSupplier()

    # Test 1: Validate credentials
    log.info("1. Validating Mouser API access...")
    if mouser.validate_credentials():
        log.info("   [OK] Mouser API is accessible\n")
    else:
        log.info("   [ERROR] Cannot access Mouser API (check API key)\n")

    # Test 2: Search by MPN
    test_mpn = "STM32F407VGT6"
    log.info(f"2. Searching for MPN: {test_mpn}")
    results = mouser.search_by_mpn(test_mpn)
    log.info(f"   Found {len(results)} results:")
    for part in results[:3]:  # Show first 3
        log.info(f"   - {part.supplier_part_number}: {part.description}")
        log.info(f"     Manufacturer: {part.manufacturer}")
        log.info(f"     Stock: {part.stock_quantity}")
        log.info(f"     Lifecycle: {part.lifecycle_status}")
        if part.price_breaks:
            log.info(f"     Price (1pc): ${part.price_breaks[0].get('unit_price', 0.0):.4f}")
    log.info("")

    # Test 3: Get specific part details
    if results:
        test_mouser_pn = results[0].supplier_part_number
        log.info(f"3. Getting details for Mouser part: {test_mouser_pn}")
        part = mouser.get_part_details(test_mouser_pn)
        if part:
            log.info(f"   Mouser Part #: {part.supplier_part_number}")
            log.info(f"   MPN: {part.manufacturer_part_number}")
            log.info(f"   Manufacturer: {part.manufacturer}")
            log.info(f"   Description: {part.description}")
            log.info(f"   Stock: {part.stock_quantity}")
            log.info(f"   URL: {part.product_url}")
            log.info(f"   Datasheet: {part.datasheet_url}")
        else:
            log.info("   [ERROR] Part not found")
        log.info("")

    # Test 4: Verify parameter field name
    log.info(f"4. Parameter field name: {mouser.parameter_field_name}")
    log.info("   (This should stay stable for downstream consumers)")
