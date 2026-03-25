"""Pydantic models for API request/response shapes."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .providers.base import SupplierPartInfo


class PartResponse(BaseModel):
    """Serialized part data for the API response."""

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

    @classmethod
    def from_supplier_part_info(
        cls, part: SupplierPartInfo, *, include_raw: bool = False
    ) -> "PartResponse":
        data = {
            "supplier": part.supplier.value,
            "supplier_part_number": part.supplier_part_number,
            "manufacturer": part.manufacturer,
            "manufacturer_part_number": part.manufacturer_part_number,
            "description": part.description,
            "datasheet_url": part.datasheet_url,
            "product_url": part.product_url,
            "stock_quantity": part.stock_quantity,
            "stock_status": part.stock_status,
            "price_breaks": part.price_breaks,
            "lifecycle_status": part.lifecycle_status,
        }
        if include_raw:
            data["extra_data"] = part.extra_data
        return cls(**data)


class ServiceEnvelope(BaseModel):
    """Standard response wrapper for all API endpoints."""

    status: str  # "ok", "not_found", "provider_error"
    supplier: str
    provider_latency_ms: int = 0
    service_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cached: bool = False
    data: Any = None
    error: str | None = None
