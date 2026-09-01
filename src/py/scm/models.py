"""
Shared contract between server and client.

This module defines the API response shapes, supplier enumeration, and field
name mappings. Both scm.client and scm.server import from here.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .generated.v1.models import (
    DetailEnvelope as DetailEnvelope,
    HealthResponse as HealthResponse,
    HttpErrorDetail as HttpErrorDetail,
    ProviderStatusResponse as ProviderStatusResponse,
    SearchEnvelope as SearchEnvelope,
    SpnBatchEnvelope as SpnBatchEnvelope,
    SpnBatchRequest as SpnBatchRequest,
    SpnEnvelope as SpnEnvelope,
    StreamDoneEvent as StreamDoneEvent,
    StreamSearchEvent as StreamSearchEvent,
    ValidationErrorDetail as ValidationErrorDetail,
)


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
    source_provider: str = ""
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


class RateLimitSnapshot(BaseModel):
    """Latest observed provider rate/quota state."""

    request_limit: int | None = None
    requests_remaining: int | None = None
    burst_limit: int | None = None
    burst_remaining: int | None = None
    reset_seconds: int | None = None
    reset_time: str | None = None
    retry_after_seconds: int | None = None
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SupplierCapabilities(BaseModel):
    """Static provider capabilities exposed to clients and GUI tools."""

    supplier: str
    provider_kind: str = "direct_supplier"
    supports_mpn_search: bool = True
    supports_keyword_search: bool = False
    supports_spn_lookup: bool = True
    supports_native_spn_batch: bool = False
    max_spn_batch_size: int = 1
    min_request_interval_seconds: float = 0.0
    rate_limit_per_minute: int | None = None
    rate_limit_per_day: int | None = None
    usage_unit: str = "requests"
    supports_quota_headers: bool = False
    notes: list[str] = Field(default_factory=list)


class SpnBatchItem(BaseModel):
    """One exact supplier part number lookup result."""

    spn: str
    status: str
    part: PartResponse | None = None
    error: str | None = None


class ServiceErrorDetail(BaseModel):
    """Sanitized, machine-readable context for a service failure."""

    code: str
    retryable: bool = False
    upstream_status_code: int | None = None
    upstream_request_id: str | None = None


class ServiceEnvelope(BaseModel):
    """Standard response wrapper for all API endpoints."""

    status: str  # "ok", "partial", "not_found", "provider_error"
    supplier: str
    parameter_field_name: str = ""
    provider_latency_ms: int = 0
    provider_capabilities: SupplierCapabilities | None = None
    rate_limit: RateLimitSnapshot | None = None
    service_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cached: bool = False
    data: Any = None
    error: str | None = None
    error_detail: ServiceErrorDetail | None = None
