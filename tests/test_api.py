"""Tests for the FastAPI HTTP layer.

Uses FastAPI's TestClient — no live server or network calls needed.
Provider calls are mocked to isolate the HTTP/auth/envelope logic.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from scm.server.main import app
from scm.server.providers.base import SupplierPartInfo
from scm.models import SupplierType


@pytest.fixture
def client():
    """TestClient with a known service token."""
    with patch("scm.server.auth.settings") as mock_settings:
        mock_settings.service_token = "test-token"
        yield TestClient(app)


def _auth_header(token="test-token"):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_no_auth_required(self, client):
        r = client.get("/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_token_returns_422(self, client):
        r = client.get("/v1/providers/status")
        assert r.status_code == 422

    def test_invalid_token_returns_401(self, client):
        r = client.get("/v1/providers/status", headers=_auth_header("wrong"))
        assert r.status_code == 401
        assert "Invalid" in r.json()["detail"]

    def test_valid_token_succeeds(self, client):
        r = client.get("/v1/providers/status", headers=_auth_header())
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Provider status
# ---------------------------------------------------------------------------

class TestProviderStatus:
    def test_returns_all_providers(self, client):
        r = client.get("/v1/providers/status", headers=_auth_header())
        providers = r.json()["providers"]
        assert "JLCPCB" in providers
        assert "LCSC" in providers
        assert "Digikey" in providers
        assert "Mouser" in providers


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _mock_part(supplier=SupplierType.JLCPCB, pn="C12345", mpn="TEST123"):
    return SupplierPartInfo(
        supplier=supplier,
        supplier_part_number=pn,
        manufacturer="TestMfr",
        manufacturer_part_number=mpn,
        description="Test part",
        stock_quantity=100,
        stock_status="in_stock",
    )


class TestSearch:
    def test_unknown_supplier(self, client):
        r = client.get("/v1/search", params={"supplier": "fake", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "provider_error"
        assert "Unknown supplier" in body["error"]

    def test_missing_params(self, client):
        r = client.get("/v1/search", headers=_auth_header())
        assert r.status_code == 422

    @patch("scm.server.routers.search.create_supplier")
    def test_search_returns_envelope(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part()]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "TEST123"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "ok"
        assert body["supplier"] == "JLCPCB"
        assert body["parameter_field_name"] == "JLCPCB Part #"
        assert isinstance(body["provider_latency_ms"], int)
        assert body["cached"] is False
        assert body["service_timestamp"]
        assert body["error"] is None
        assert len(body["data"]) == 1

    @patch("scm.server.routers.search.create_supplier")
    def test_search_includes_rate_limit_metadata(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part(supplier=SupplierType.DIGIKEY)]
        mock_supplier.rate_limit_status.return_value = {"limit": 1000, "remaining": 997}
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "digikey", "mpn": "TEST123"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "ok"
        assert body["rate_limit"] == {"limit": 1000, "remaining": 997}
        assert r.headers["X-RateLimit-Limit"] == "1000"
        assert r.headers["X-RateLimit-Remaining"] == "997"

    @patch("scm.server.routers.search.create_supplier")
    def test_search_not_found(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = []
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "ZZZZ"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "not_found"
        assert body["data"] == []

    @patch("scm.server.routers.search.create_supplier")
    def test_search_provider_error(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.side_effect = RuntimeError("connection timeout")
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "provider_error"
        assert "connection timeout" in body["error"]

    @patch("scm.server.routers.search.create_supplier")
    def test_search_part_shape(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part()]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "TEST123"}, headers=_auth_header())
        part = r.json()["data"][0]

        assert part["supplier"] == "JLCPCB"
        assert part["supplier_part_number"] == "C12345"
        assert part["manufacturer_part_number"] == "TEST123"
        assert part["stock_quantity"] == 100
        assert part["stock_status"] == "in_stock"
        # extra_data should be null when not requested
        assert part.get("extra_data") is None

    @patch("scm.server.routers.search.create_supplier")
    def test_include_raw(self, mock_create, client):
        p = _mock_part()
        p.extra_data = {"debug": "info"}
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [p]
        mock_create.return_value = mock_supplier

        r = client.get(
            "/v1/search",
            params={"supplier": "jlcpcb", "mpn": "X", "include_raw": "true"},
            headers=_auth_header(),
        )
        part = r.json()["data"][0]
        assert "extra_data" in part
        assert part["extra_data"] == {"debug": "info"}

    def test_supplier_case_insensitive(self, client):
        """Supplier name should be case-insensitive."""
        with patch("scm.server.routers.search.create_supplier") as mock_create:
            mock_supplier = MagicMock()
            mock_supplier.search_by_mpn.return_value = [_mock_part()]
            mock_create.return_value = mock_supplier

            for name in ["JLCPCB", "jlcpcb", "Jlcpcb"]:
                r = client.get("/v1/search", params={"supplier": name, "mpn": "X"}, headers=_auth_header())
                assert r.json()["status"] == "ok", f"Failed for supplier name: {name}"


# ---------------------------------------------------------------------------
# None field handling (regression: Digikey returns None for datasheet_url)
# ---------------------------------------------------------------------------

class TestNoneFields:
    """Regression tests for providers returning None in string fields."""

    @patch("scm.server.routers.search.create_supplier")
    def test_none_datasheet_url(self, mock_create, client):
        """Digikey can return DatasheetUrl: None for some variants."""
        part = _mock_part(supplier=SupplierType.DIGIKEY, pn="256-W25Q16RVSSJQTR-ND")
        part.datasheet_url = None
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "digikey", "mpn": "W25Q16RVSS"}, headers=_auth_header())
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["data"][0]["datasheet_url"] == ""

    @patch("scm.server.routers.search.create_supplier")
    def test_none_product_url(self, mock_create, client):
        part = _mock_part()
        part.product_url = None
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        assert r.json()["data"][0]["product_url"] == ""

    @patch("scm.server.routers.search.create_supplier")
    def test_none_description(self, mock_create, client):
        part = _mock_part()
        part.description = None
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        assert r.json()["data"][0]["description"] == ""

    @patch("scm.server.routers.search.create_supplier")
    def test_none_manufacturer(self, mock_create, client):
        part = _mock_part()
        part.manufacturer = None
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        assert r.json()["data"][0]["manufacturer"] == ""

    @patch("scm.server.routers.search.create_supplier")
    def test_none_lifecycle_status(self, mock_create, client):
        part = _mock_part()
        part.lifecycle_status = None
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        assert r.json()["data"][0]["lifecycle_status"] == ""

    @patch("scm.server.routers.search.create_supplier")
    def test_all_none_string_fields(self, mock_create, client):
        """Worst case: every optional string field is None."""
        part = SupplierPartInfo(
            supplier=SupplierType.DIGIKEY,
            supplier_part_number="TEST-ND",
            manufacturer=None,
            manufacturer_part_number=None,
            description=None,
            datasheet_url=None,
            product_url=None,
            stock_quantity=0,
            stock_status="unknown",
            lifecycle_status=None,
        )
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [part]
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "digikey", "mpn": "X"}, headers=_auth_header())
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        p = body["data"][0]
        assert p["manufacturer"] == ""
        assert p["manufacturer_part_number"] == ""
        assert p["description"] == ""
        assert p["datasheet_url"] == ""
        assert p["product_url"] == ""
        assert p["lifecycle_status"] == ""


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class TestDetail:
    @patch("scm.server.routers.detail.create_supplier")
    def test_detail_returns_envelope(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.get_part_details.return_value = _mock_part()
        mock_create.return_value = mock_supplier

        r = client.get("/v1/detail", params={"supplier": "jlcpcb", "part": "C12345"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "ok"
        assert body["supplier"] == "JLCPCB"
        assert isinstance(body["data"], dict)
        assert body["data"]["supplier_part_number"] == "C12345"

    @patch("scm.server.routers.detail.create_supplier")
    def test_detail_not_found(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.get_part_details.return_value = None
        mock_create.return_value = mock_supplier

        r = client.get("/v1/detail", params={"supplier": "jlcpcb", "part": "C99999999"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "not_found"
        assert body["data"] is None

    def test_detail_unknown_supplier(self, client):
        r = client.get("/v1/detail", params={"supplier": "nope", "part": "X"}, headers=_auth_header())
        assert r.json()["status"] == "provider_error"

    def test_detail_missing_params(self, client):
        r = client.get("/v1/detail", headers=_auth_header())
        assert r.status_code == 422
