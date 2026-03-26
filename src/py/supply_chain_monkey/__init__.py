"""
Supply Chain Monkey - Electronic Component Supplier Service

Provides a standardized interface for querying component suppliers
(JLCPCB, LCSC, Digikey, Mouser) via HTTP API or direct Python use.
"""

from .providers.base import (
    IMPLEMENTED_SUPPLIERS,
    SupplierInterface,
    SupplierPartInfo,
    SupplierType,
    create_supplier,
    get_available_suppliers,
)

__version__ = "1.0.0"

__all__ = [
    "SupplierType",
    "SupplierPartInfo",
    "SupplierInterface",
    "create_supplier",
    "get_available_suppliers",
    "IMPLEMENTED_SUPPLIERS",
]
