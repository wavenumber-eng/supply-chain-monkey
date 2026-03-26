"""Unit tests for provider utilities (no network calls)."""

from scm.server.providers.base import resolve_stock, SupplierPartInfo
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
