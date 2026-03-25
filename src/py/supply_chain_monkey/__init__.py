"""
Supply Chain Monkey - Generic Supplier Interface

This module provides a standardized interface for interacting with component
suppliers (JLCPCB, Digikey, Mouser, etc.) for PCB parts sourcing.

Key Components:
    - SupplierType: Enum of supported suppliers
    - SupplierPartInfo: Standardized data container
    - SupplierInterface: Abstract base class
    - create_supplier(): Factory function for creating instances

Quick Start:
    >>> from supply_chain_monkey import create_supplier, SupplierType
    >>>
    >>> # Create a supplier instance
    >>> jlc = create_supplier(SupplierType.JLCPCB)
    >>>
    >>> # Search by manufacturer part number
    >>> results = jlc.search_by_mpn("STM32F407VGT6")
    >>> for part in results:
    ...     log.info(f"{part.supplier_part_number}: {part.stock_quantity} in stock")
    >>>
    >>> # Get specific part details
    >>> part = jlc.get_part_details("C2040")
    >>> log.info(part.description)
    >>>
    >>> # Auto-fill Part parameter field
    >>> from data_models import Part
    >>> part_obj = Part()
    >>> part_obj[jlc.parameter_field_name] = part.supplier_part_number

Multi-Supplier Example:
    >>> from supply_chain_monkey import create_supplier, SupplierType, get_available_suppliers
    >>>
    >>> mpn = "STM32F407VGT6"
    >>>
    >>> # Search all available suppliers
    >>> all_results = []
    >>> for supplier_type in get_available_suppliers():
    ...     try:
    ...         supplier = create_supplier(supplier_type)
    ...         results = supplier.search_by_mpn(mpn)
    ...         all_results.extend(results)
    ...     except Exception as e:
    ...         log.info(f"Skipping {supplier_type.value}: {e}")
    >>>
    >>> # Display results from all suppliers
    >>> for part in all_results:
    ...     log.info(f"{part.supplier.value}: {part.supplier_part_number} - ${part.price_breaks[0]}")
"""

# Import core classes and functions for easy access
import logging

# Import core interface (always loaded)
from .supplier_interface import (
    IMPLEMENTED_SUPPLIERS,
    SupplierInterface,
    SupplierPartInfo,
    SupplierType,
    create_supplier,
    get_available_suppliers,
)
from .env import ensure_env_loaded, get_env_file_path, load_env_file

# Import legacy types (lightweight, always loaded)
from .jlc_scraper import JLCPartInfo
from .lcsc_scraper import LCSCPartInfo

log = logging.getLogger(__name__)


# =============================================================================
# Lazy Loading for Supplier Implementations
# =============================================================================


def __getattr__(name: str):
    """
    Lazy import for supplier implementations.

    This defers loading of supplier modules until they're actually used,
    improving import time and reducing memory usage.
    """
    if name == "JLCPCBSupplier":
        from .jlcpcb_supplier import JLCPCBSupplier

        return JLCPCBSupplier
    elif name == "LCSCSupplier":
        from .lcsc_supplier import LCSCSupplier

        return LCSCSupplier
    elif name == "DigikeySupplier":
        from .digikey_supplier import DigikeySupplier

        return DigikeySupplier
    elif name == "MouserSupplier":
        from .mouser_supplier import MouserSupplier

        return MouserSupplier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Version info
__version__ = "0.1.0"

# Public API
__all__ = [
    # Core interface
    "SupplierType",
    "SupplierPartInfo",
    "SupplierInterface",
    "create_supplier",
    "get_available_suppliers",
    "IMPLEMENTED_SUPPLIERS",
    "load_env_file",
    "get_env_file_path",
    "ensure_env_loaded",

    # Implementations
    "JLCPCBSupplier",
    "LCSCSupplier",
    "DigikeySupplier",
    "MouserSupplier",

    # Legacy types
    "JLCPartInfo",
    "LCSCPartInfo",
]
