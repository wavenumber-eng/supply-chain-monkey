"""
LCSC Supplier Implementation

Uses LCSC's internal JSON API (same endpoints the website frontend calls).
No API key required.
"""

import logging

from .base import SupplierInterface, SupplierPartInfo, SupplierType, resolve_stock
from .lcsc_api import search_lcsc as _api_search, get_lcsc_detail as _api_detail

log = logging.getLogger(__name__)


class LCSCSupplier(SupplierInterface):
    """
    LCSC implementation of the supplier interface.

    Uses LCSC's internal JSON API for search and detail lookups.
    No credentials required.
    """

    def __init__(self, **credentials):
        super().__init__(**credentials)

    @property
    def supplier_type(self) -> SupplierType:
        return SupplierType.LCSC

    @property
    def parameter_field_name(self) -> str:
        return "LCSC Part #"

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """Search LCSC by manufacturer part number."""
        try:
            products = _api_search(manufacturer_part_number)
            return [self._convert(p) for p in products]
        except Exception as e:
            log.info("Error searching LCSC for %s: %s", manufacturer_part_number, e)
            return []

    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """Get detail for a specific LCSC C code."""
        try:
            product = _api_detail(supplier_part_number)
            if not product:
                return None

            expected_mpn = kwargs.get("expected_mpn", "")
            if expected_mpn and product.product_model:
                if (expected_mpn.upper().replace("-", "").replace(" ", "")
                        != product.product_model.upper().replace("-", "").replace(" ", "")):
                    return None

            return self._convert(product)
        except Exception as e:
            log.info("Error getting LCSC details for %s: %s", supplier_part_number, e)
            return None

    def validate_credentials(self) -> bool:
        try:
            result = _api_detail("C1")
            return result is not None
        except Exception:
            return False

    @staticmethod
    def _convert(product) -> SupplierPartInfo:
        stock_qty, stock_status = resolve_stock(product.stock, product.lifecycle)
        return SupplierPartInfo(
            supplier=SupplierType.LCSC,
            supplier_part_number=product.product_code,
            manufacturer=product.brand,
            manufacturer_part_number=product.product_model,
            description=product.description,
            product_url=product.product_url,
            stock_quantity=stock_qty,
            stock_status=stock_status,
            datasheet_url=product.datasheet_url,
            price_breaks=product.price_breaks,
            lifecycle_status=product.lifecycle,
            extra_data={"package": product.package},
        )
