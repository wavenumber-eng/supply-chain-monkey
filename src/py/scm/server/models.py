"""Server-side model helpers.

Re-exports shared contract models and adds the from_supplier_part_info bridge.
"""

from scm.models import PartResponse, ServiceEnvelope
from .providers.base import SupplierPartInfo


def part_response_from_info(
    part: SupplierPartInfo, *, include_raw: bool = False
) -> PartResponse:
    """Convert an internal SupplierPartInfo to the API contract PartResponse."""
    data = {
        "supplier": part.supplier.value,
        "supplier_part_number": part.supplier_part_number or "",
        "manufacturer": part.manufacturer or "",
        "manufacturer_part_number": part.manufacturer_part_number or "",
        "description": part.description or "",
        "datasheet_url": part.datasheet_url or "",
        "product_url": part.product_url or "",
        "stock_quantity": part.stock_quantity or 0,
        "stock_status": part.stock_status or "unknown",
        "price_breaks": part.price_breaks or [],
        "lifecycle_status": part.lifecycle_status or "",
        "packaging": part.extra_data.get("packaging", "") if part.extra_data else "",
    }
    if include_raw:
        data["extra_data"] = part.extra_data
    return PartResponse(**data)
