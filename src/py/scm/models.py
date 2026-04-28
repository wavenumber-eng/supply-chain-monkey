"""
Shared contract between server and client.

This module defines the API response shapes, supplier enumeration, and field
name mappings. Both scm.client and scm.server import from here.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SupplierType(str, Enum):
    """Supported component suppliers."""

    JLCPCB = "JLCPCB"
    LCSC = "LCSC"
    DIGIKEY = "Digikey"
    MOUSER = "Mouser"


# All supplier keys (lowercase) for validation and iteration
SUPPLIERS = [s.value.lower() for s in SupplierType]

# Maps supplier to the Part parameter field name used by downstream consumers
PARAMETER_FIELD_NAMES = {
    SupplierType.JLCPCB: "JLCPCB Part #",
    SupplierType.LCSC: "LCSC Part #",
    SupplierType.DIGIKEY: "Digikey Part #",
    SupplierType.MOUSER: "Mouser Part #",
}

# Lookup by lowercase name
SUPPLIER_LOOKUP = {s.value.lower(): s for s in SupplierType}


class PartResponse(BaseModel):
    """Serialized part data in API responses."""

    supplier: str
    supplier_part_number: str
    manufacturer: str
    manufacturer_part_number: str
    description: str = ""
    datasheet_url: str = ""
    product_url: str = ""
    stock_quantity: int = 0
    stock_status: str = "unknown"
    price_breaks: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_status: str = ""
    packaging: str = ""
    extra_data: dict[str, Any] | None = None


class ServiceEnvelope(BaseModel):
    """Standard response wrapper for all API endpoints."""

    status: str  # "ok", "not_found", "provider_error"
    supplier: str
    parameter_field_name: str = ""
    provider_latency_ms: int = 0
    rate_limit: dict[str, int] | None = None
    service_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cached: bool = False
    data: Any = None
    error: str | None = None
