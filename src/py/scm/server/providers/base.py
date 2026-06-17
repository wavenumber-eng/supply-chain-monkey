"""
Generic Supplier Interface for PCB Component Sourcing

This module provides an abstract interface for interacting with different
component suppliers (JLCPCB, LCSC, Digikey, etc.) in a standardized way.

Architecture:
    - SupplierType: Enum of supported suppliers
    - SupplierPartInfo: Standardized data container for part information
    - SupplierInterface: Abstract base class that all suppliers implement
    - create_supplier(): Factory function for creating supplier instances

Usage Example:
    >>> from scm.server.providers import create_supplier, SupplierType
    >>>
    >>> # Create JLCPCB supplier instance
    >>> jlc = create_supplier(SupplierType.JLCPCB)
    >>>
    >>> # Search by manufacturer part number
    >>> results = jlc.search_by_mpn("STM32F407VGT6")
    >>> for part in results:
    ...     log.info(f"{part.supplier_part_number}: {part.stock_quantity} in stock")
    >>>
    >>> # Get specific part details
    >>> part = jlc.get_part_details("C2040")
    >>> if part:
    ...     log.info(f"{part.description}")
    >>>
    >>> # Get the Part parameter field name for this supplier
    >>> field_name = jlc.parameter_field_name  # "JLCPCB Part #"
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from scm.models import RateLimitSnapshot, SupplierCapabilities, SupplierType

log = logging.getLogger(__name__)


@dataclass
class SupplierPartInfo:
    """
    Standardized container for supplier part information.

    This normalizes data from different supplier APIs into a common format,
    making it easy to work with parts from multiple sources.

    Core Fields:
        supplier: Which supplier this part is from
        supplier_part_number: Supplier's unique identifier (e.g., "C2040", "296-12345-1-ND")
        manufacturer: Manufacturer name (e.g., "STMicroelectronics")
        manufacturer_part_number: Manufacturer's part number (MPN)

    Detail Fields:
        description: Human-readable part description
        datasheet_url: Link to datasheet PDF
        product_url: Link to supplier's product page

    Availability Fields:
        stock_quantity: Number of units in stock
        price_breaks: List of quantity/price pairs [{"qty": 1, "price": 0.50}, ...]
        lifecycle_status: "Active", "Obsolete", "NRND" (Not Recommended for New Designs), etc.

    Metadata:
        extra_data: Supplier-specific fields that don't fit standard schema

    Example:
        >>> part = SupplierPartInfo(
        ...     supplier=SupplierType.JLCPCB,
        ...     supplier_part_number="C2040",
        ...     manufacturer="Samsung",
        ...     manufacturer_part_number="CL10A106KQ8NNNC",
        ...     description="10uF 6.3V X5R 0603",
        ...     stock_quantity=50000
        ... )
        >>> part.to_dict()
    """

    # Core identification
    supplier: SupplierType
    supplier_part_number: str
    manufacturer: str | None
    manufacturer_part_number: str | None
    source_provider: str = ""

    # Details
    description: str | None = ""
    datasheet_url: str | None = ""
    product_url: str | None = ""

    # Availability & pricing
    stock_quantity: int = 0
    stock_status: str = "unknown"  # "in_stock", "out_of_stock", "unknown", "discontinued"
    price_breaks: list[dict[str, Any]] = field(default_factory=list)
    lifecycle_status: str | None = ""

    # Additional metadata (supplier-specific fields)
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of part info
        """
        return {
            'supplier': self.supplier.value,
            'source_provider': self.source_provider,
            'supplier_part_number': self.supplier_part_number,
            'manufacturer': self.manufacturer,
            'manufacturer_part_number': self.manufacturer_part_number,
            'description': self.description,
            'datasheet_url': self.datasheet_url,
            'product_url': self.product_url,
            'stock_quantity': self.stock_quantity,
            'stock_status': self.stock_status,
            'price_breaks': self.price_breaks,
            'lifecycle_status': self.lifecycle_status,
            'extra_data': self.extra_data
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"SupplierPartInfo({self.supplier.value}: {self.supplier_part_number}, "
                f"MPN={self.manufacturer_part_number}, stock={self.stock_quantity})")


class SupplierInterface(ABC):
    """
    Abstract base class for supplier API clients.

    Each supplier (JLCPCB, LCSC, Digikey, etc.) implements this interface
    to provide standardized access to their parts database. This allows the
    rest of the codebase to work with any supplier using the same API.

    Key Responsibilities:
        1. Search for parts by manufacturer part number (MPN)
        2. Get detailed information for specific supplier part numbers
        3. Map supplier part numbers to Part parameter fields

    Implementation Notes:
        - Subclasses should handle their own authentication/credentials
        - All methods should return standardized SupplierPartInfo objects
        - Errors should be handled gracefully (return empty list or None)
        - Rate limiting and API quotas are implementation-specific

    Example Implementation:
        >>> class JLCPCBSupplier(SupplierInterface):
        ...     @property
        ...     def supplier_type(self):
        ...         return SupplierType.JLCPCB
        ...
        ...     @property
        ...     def parameter_field_name(self):
        ...         return "JLCPCB Part #"
        ...
        ...     def search_by_mpn(self, mpn, **kwargs):
        ...         # Implementation here
        ...         pass
    """

    def __init__(self, **credentials):
        """
        Initialize supplier client with credentials.

        Args:
            **credentials: Supplier-specific credentials
                Examples:
                    - api_key="...", api_secret="..."  (JLCPCB, Digikey)
                    - client_id="...", client_secret="..."  (Some OAuth APIs)
                    - username="...", password="..."  (Basic auth)
        """
        self.credentials = credentials
        self._rate_limit_snapshot: RateLimitSnapshot | None = None

    @property
    def capabilities(self) -> SupplierCapabilities:
        """Return provider capabilities for planning batch and quota behavior."""
        return get_default_supplier_capabilities(self.supplier_type)

    @property
    @abstractmethod
    def supplier_type(self) -> SupplierType:
        """
        Return the supplier type for this implementation.

        Returns:
            SupplierType enum value

        Example:
            >>> supplier.supplier_type
            SupplierType.JLCPCB
        """
        pass

    @property
    @abstractmethod
    def parameter_field_name(self) -> str:
        """
        Return the Part parameter field name for this supplier.

        This is the field name used in Part objects to store the supplier's
        part number. It must stay stable for downstream tools such as
        `lib_cruncher`, but is no longer coupled to the old monolith settings layer.

        This enables automatic mapping:
            part[supplier.parameter_field_name] = supplier_part_number

        Returns:
            Field name as it appears in Part dictionaries

        Examples:
            - "JLCPCB Part #"
            - "LCSC Part #"
            - "Digikey Part #"

        Usage:
            >>> jlc = create_supplier(SupplierType.JLCPCB)
            >>> part = Part()
            >>> part[jlc.parameter_field_name] = "C2040"  # Sets "JLCPCB Part #"
        """
        pass

    @abstractmethod
    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search for parts by manufacturer part number.

        This is the primary search method - given an MPN, find all matching
        parts from this supplier. Suppliers may have multiple entries for the
        same MPN (different packaging, cut tape vs reel, etc.).

        Args:
            manufacturer_part_number: MPN to search for (e.g., "STM32F407VGT6")
            **kwargs: Supplier-specific options
                Common options:
                    - page: int = 1
                    - page_size: int = 20
                    - verify_parts: bool = True
                    - include_obsolete: bool = False

        Returns:
            List of matching SupplierPartInfo objects (empty list if none found)

        Raises:
            Should NOT raise exceptions - return empty list on error
            (Allows graceful degradation when supplier APIs are down)

        Example:
            >>> results = supplier.search_by_mpn("GCM1555C1H100FA16D")
            >>> if results:
            ...     for part in results:
            ...         log.info(f"{part.supplier_part_number}: {part.description}")
            ... else:
            ...     log.info("No parts found")
        """
        pass

    @abstractmethod
    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """
        Get detailed information for a specific supplier part number.

        This is for when you already know the supplier's part number and want
        full details (stock, pricing, lifecycle status, etc.).

        Args:
            supplier_part_number: Supplier's unique identifier
                Examples:
                    - "C2040" (JLCPCB/LCSC)
                    - "296-12345-1-ND" (Digikey)
            **kwargs: Supplier-specific options
                Common options:
                    - expected_mpn: str (for validation)
                    - include_pricing: bool = True

        Returns:
            SupplierPartInfo object if found, None if not found or error

        Raises:
            Should NOT raise exceptions - return None on error

        Example:
            >>> part = supplier.get_part_details("C2040")
            >>> if part:
            ...     log.info(f"Stock: {part.stock_quantity}")
            ...     log.info(f"Description: {part.description}")
            ... else:
            ...     log.info("Part not found")
        """
        pass

    def validate_credentials(self) -> bool:
        """
        Validate that credentials are working.

        This is useful for checking API keys before attempting real operations.
        Default implementation tries a simple search - override for better
        supplier-specific validation if available.

        Returns:
            True if credentials are valid and API is accessible, False otherwise

        Example:
            >>> supplier = create_supplier(SupplierType.JLCPCB, api_key="test")
            >>> if not supplier.validate_credentials():
            ...     log.info("Invalid credentials!")
        """
        try:
            # Attempt a simple search with a known part
            self.search_by_mpn("TEST_VALIDATION_12345")
            return True
        except Exception:
            return False

    def get_part_details_batch(
        self, supplier_part_numbers: list[str], **kwargs
    ) -> dict[str, SupplierPartInfo | None]:
        """Get details for multiple exact supplier part numbers.

        Providers with a native batch API should override this method. The
        default implementation preserves compatibility by looping single lookups.
        """
        results: dict[str, SupplierPartInfo | None] = {}
        for supplier_part_number in supplier_part_numbers:
            cleaned = supplier_part_number.strip()
            if cleaned:
                results[cleaned] = self.get_part_details(cleaned, **kwargs)
        return results

    def get_rate_limit_snapshot(self) -> RateLimitSnapshot | None:
        """Return the latest observed provider quota state, if known."""
        return self._rate_limit_snapshot


def _header_value(headers: Mapping[str, str], *names: str) -> str | None:
    normalized = {key.lower(): value for key, value in headers.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _parse_int_header(headers: Mapping[str, str], *names: str) -> int | None:
    value = _header_value(headers, *names)
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def rate_limit_snapshot_from_headers(
    headers: Mapping[str, str],
) -> RateLimitSnapshot | None:
    """Parse common provider quota headers into a normalized snapshot."""
    request_limit = _parse_int_header(headers, "X-RateLimit-Limit", "RateLimit-Limit")
    requests_remaining = _parse_int_header(
        headers,
        "X-RateLimit-Remaining",
        "RateLimit-Remaining",
    )
    burst_limit = _parse_int_header(headers, "X-BurstLimit-Limit")
    burst_remaining = _parse_int_header(headers, "X-BurstLimit-Remaining")
    reset_seconds = _parse_int_header(
        headers,
        "X-RateLimit-Reset",
        "X-BurstLimit-Reset",
        "RateLimit-Reset",
    )
    retry_after_seconds = _parse_int_header(headers, "Retry-After")
    reset_time = _header_value(
        headers,
        "X-RateLimit-ResetTime",
        "X-BurstLimit-ResetTime",
    )

    if not any(
        value is not None
        for value in (
            request_limit,
            requests_remaining,
            burst_limit,
            burst_remaining,
            reset_seconds,
            retry_after_seconds,
            reset_time,
        )
    ):
        return None

    return RateLimitSnapshot(
        request_limit=request_limit,
        requests_remaining=requests_remaining,
        burst_limit=burst_limit,
        burst_remaining=burst_remaining,
        reset_seconds=reset_seconds,
        reset_time=reset_time,
        retry_after_seconds=retry_after_seconds,
        observed_at=datetime.now(timezone.utc).isoformat(),
    )


def get_default_supplier_capabilities(
    supplier_type: SupplierType,
) -> SupplierCapabilities:
    """Return static capabilities without requiring provider credentials."""
    if supplier_type == SupplierType.JLCPCB:
        return SupplierCapabilities(
            supplier=supplier_type.value,
            supports_mpn_search=True,
            supports_spn_lookup=True,
            supports_native_spn_batch=False,
            max_spn_batch_size=1,
            usage_unit="requests",
            notes=[
                "MPN search is scraper-backed.",
                "Native SPN batch is available when JLC OpenAPI credentials are configured.",
            ],
        )
    if supplier_type == SupplierType.LCSC:
        return SupplierCapabilities(
            supplier=supplier_type.value,
            supports_mpn_search=True,
            supports_spn_lookup=True,
            supports_native_spn_batch=False,
            max_spn_batch_size=1,
            usage_unit="requests",
            notes=["Current adapter uses LCSC JSON endpoints."],
        )
    if supplier_type == SupplierType.DIGIKEY:
        return SupplierCapabilities(
            supplier=supplier_type.value,
            supports_mpn_search=True,
            supports_spn_lookup=True,
            supports_native_spn_batch=False,
            max_spn_batch_size=1,
            min_request_interval_seconds=0.2,
            rate_limit_per_minute=120,
            rate_limit_per_day=1000,
            usage_unit="requests",
            supports_quota_headers=True,
        )
    if supplier_type == SupplierType.MOUSER:
        return SupplierCapabilities(
            supplier=supplier_type.value,
            supports_mpn_search=True,
            supports_spn_lookup=True,
            supports_native_spn_batch=True,
            max_spn_batch_size=10,
            usage_unit="requests",
            notes=["Native exact SPN batch uses pipe-separated part numbers."],
        )
    return SupplierCapabilities(supplier=supplier_type.value)


def create_supplier(supplier_type: SupplierType, **credentials) -> SupplierInterface:
    """
    Factory function to create supplier client instances.

    This is the primary way to instantiate supplier clients. It handles
    importing the correct implementation and passing credentials.

    Args:
        supplier_type: Type of supplier to create (from SupplierType enum)
        **credentials: Supplier-specific authentication credentials

    Returns:
        Configured SupplierInterface implementation

    Raises:
        ValueError: If supplier_type is not supported
        ImportError: If supplier implementation module is not available

    Examples:
        >>> # JLCPCB (no credentials required for scraper)
        >>> jlc = create_supplier(SupplierType.JLCPCB)
        >>>
        >>> # Digikey (requires API credentials)
        >>> digikey = create_supplier(
        ...     SupplierType.DIGIKEY,
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret"
        ... )
    """
    if supplier_type == SupplierType.JLCPCB:
        from .jlc import JLCPCBSupplier
        return JLCPCBSupplier(**credentials)

    elif supplier_type == SupplierType.LCSC:
        from .lcsc import LCSCSupplier
        return LCSCSupplier(**credentials)

    elif supplier_type == SupplierType.DIGIKEY:
        from .digikey import DigikeySupplier
        return DigikeySupplier(**credentials)

    elif supplier_type == SupplierType.MOUSER:
        from .mouser import MouserSupplier
        return MouserSupplier(**credentials)

    else:
        raise ValueError(
            f"Unsupported supplier type: {supplier_type}. "
            f"Available types: {', '.join([s.value for s in IMPLEMENTED_SUPPLIERS])}"
        )


def resolve_stock(raw_value, lifecycle_status: str | None = "") -> tuple[int, str]:
    """Convert a raw stock value into (stock_quantity, stock_status).

    Handles numeric, string, None, and edge cases like "--".
    """
    if (lifecycle_status or "").lower() in ("discontinued", "obsolete", "eol", "end of life"):
        try:
            qty = int(raw_value)
        except (TypeError, ValueError):
            qty = 0
        return qty, "discontinued"

    if raw_value is None or raw_value == "":
        return 0, "unknown"

    if isinstance(raw_value, str):
        cleaned = raw_value.strip().replace(",", "")
        if cleaned in ("--", "-", "N/A", "n/a"):
            return 0, "unknown"
        try:
            qty = int(cleaned)
        except ValueError:
            return 0, "unknown"
    else:
        try:
            qty = int(raw_value)
        except (TypeError, ValueError):
            return 0, "unknown"

    if qty > 0:
        return qty, "in_stock"
    return 0, "out_of_stock"


# List of implemented suppliers (suppliers that have working implementations)
IMPLEMENTED_SUPPLIERS = [
    SupplierType.JLCPCB,
    SupplierType.LCSC,
    SupplierType.DIGIKEY,
    SupplierType.MOUSER,
    # Add new suppliers here as they are implemented
]


# Convenience function for getting all available suppliers
def get_available_suppliers() -> list[SupplierType]:
    """
    Get list of implemented supplier types.

    This returns only suppliers that have working implementations,
    not all suppliers in the SupplierType enum.

    Returns:
        List of SupplierType enum values for implemented suppliers

    Example:
        >>> suppliers = get_available_suppliers()
        >>> for supplier in suppliers:
        ...     log.info(supplier.value)
        JLCPCB
        LCSC
        Digikey
    """
    return IMPLEMENTED_SUPPLIERS.copy()
