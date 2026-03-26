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
        "packaging": part.extra_data.get("packaging", "") if part.extra_data else "",
    }
    if include_raw:
        data["extra_data"] = part.extra_data
    return PartResponse(**data)
