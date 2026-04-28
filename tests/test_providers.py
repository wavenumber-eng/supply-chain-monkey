"""Unit tests for provider utilities (no network calls)."""

from scm.server.providers.base import resolve_stock, SupplierPartInfo
from scm.server.providers.digikey import DigikeySupplier
from scm.models import SupplierType


class TestResolveStock:
    def test_positive_int(self):
        assert resolve_stock(100) == (100, "in_stock")

    def test_zero_int(self):
        assert resolve_stock(0) == (0, "out_of_stock")

    def test_positive_string(self):
        assert resolve_stock("500") == (500, "in_stock")

    def test_zero_string(self):
        assert resolve_stock("0") == (0, "out_of_stock")

    def test_dash_dash(self):
        assert resolve_stock("--") == (0, "unknown")

    def test_single_dash(self):
        assert resolve_stock("-") == (0, "unknown")

    def test_empty_string(self):
        assert resolve_stock("") == (0, "unknown")

    def test_none(self):
        assert resolve_stock(None) == (0, "unknown")

    def test_na_string(self):
        assert resolve_stock("N/A") == (0, "unknown")

    def test_commas_in_number(self):
        assert resolve_stock("1,234") == (1234, "in_stock")

    def test_discontinued_lifecycle(self):
        qty, status = resolve_stock(50, "Discontinued")
        assert status == "discontinued"
        assert qty == 50

    def test_obsolete_lifecycle(self):
        qty, status = resolve_stock(0, "Obsolete")
        assert status == "discontinued"
        assert qty == 0

    def test_eol_lifecycle(self):
        _, status = resolve_stock(10, "End of Life")
        assert status == "discontinued"

    def test_none_lifecycle(self):
        """Mouser sometimes returns None for lifecycle."""
        assert resolve_stock(100, None) == (100, "in_stock")


class TestSupplierPartInfoStockStatus:
    def test_default_stock_status(self):
        part = SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
            supplier_part_number="C1",
            manufacturer="Test",
            manufacturer_part_number="TEST1",
        )
        assert part.stock_status == "unknown"
        assert part.stock_quantity == 0

    def test_to_dict_includes_stock_status(self):
        part = SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
            supplier_part_number="C1",
            manufacturer="Test",
            manufacturer_part_number="TEST1",
            stock_quantity=50,
            stock_status="in_stock",
        )
        d = part.to_dict()
        assert d["stock_status"] == "in_stock"
        assert d["stock_quantity"] == 50


class TestPartResponseConversion:
    """Regression: part_response_from_info must handle None string fields."""

    def test_none_datasheet_url_converts(self):
        from scm.server.models import part_response_from_info
        part = SupplierPartInfo(
            supplier=SupplierType.DIGIKEY,
            supplier_part_number="256-W25Q16RVSSJQTR-ND",
            manufacturer="Winbond",
            manufacturer_part_number="W25Q16RVSS",
            datasheet_url=None,
            product_url="https://digikey.com/...",
            stock_quantity=0,
            stock_status="out_of_stock",
        )
        pr = part_response_from_info(part)
        assert pr.datasheet_url == ""

    def test_all_none_strings_convert(self):
        from scm.server.models import part_response_from_info
        part = SupplierPartInfo(
            supplier=SupplierType.DIGIKEY,
            supplier_part_number="TEST-ND",
            manufacturer=None,
            manufacturer_part_number=None,
            description=None,
            datasheet_url=None,
            product_url=None,
            lifecycle_status=None,
        )
        pr = part_response_from_info(part)
        assert pr.manufacturer == ""
        assert pr.manufacturer_part_number == ""
        assert pr.description == ""
        assert pr.datasheet_url == ""
        assert pr.product_url == ""
        assert pr.lifecycle_status == ""


class TestDigikeyRateLimitCapture:
    def test_capture_rate_limit_headers(self):
        supplier = DigikeySupplier(client_id="client", client_secret="secret")

        supplier._capture_rate_limit(
            {
                "X-RateLimit-Limit": "1000",
                "X-RateLimit-Remaining": "997",
            }
        )

        assert supplier.rate_limit_status == {"limit": 1000, "remaining": 997}

    def test_ignores_missing_or_non_integer_rate_limit_headers(self):
        supplier = DigikeySupplier(client_id="client", client_secret="secret")

        supplier._capture_rate_limit(
            {
                "X-RateLimit-Limit": "not-a-number",
            }
        )

        assert supplier.rate_limit_status == {}
