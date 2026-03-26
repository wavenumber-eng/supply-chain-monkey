"""Tests for the FastAPI HTTP layer.

Uses FastAPI's TestClient — no live server or network calls needed.
Provider calls are mocked to isolate the HTTP/auth/envelope logic.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from supply_chain_monkey.main import app
from supply_chain_monkey.providers.base import SupplierPartInfo, SupplierType


@pytest.fixture
def client():
    """TestClient with a known service token."""
    with patch("supply_chain_monkey.auth.settings") as mock_settings:
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

    @patch("supply_chain_monkey.routers.search.create_supplier")
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

    @patch("supply_chain_monkey.routers.search.create_supplier")
    def test_search_not_found(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = []
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "ZZZZ"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "not_found"
        assert body["data"] == []

    @patch("supply_chain_monkey.routers.search.create_supplier")
    def test_search_provider_error(self, mock_create, client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.side_effect = RuntimeError("connection timeout")
        mock_create.return_value = mock_supplier

        r = client.get("/v1/search", params={"supplier": "jlcpcb", "mpn": "X"}, headers=_auth_header())
        body = r.json()

        assert body["status"] == "provider_error"
        assert "connection timeout" in body["error"]

    @patch("supply_chain_monkey.routers.search.create_supplier")
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

    @patch("supply_chain_monkey.routers.search.create_supplier")
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
        with patch("supply_chain_monkey.routers.search.create_supplier") as mock_create:
            mock_supplier = MagicMock()
            mock_supplier.search_by_mpn.return_value = [_mock_part()]
            mock_create.return_value = mock_supplier

            for name in ["JLCPCB", "jlcpcb", "Jlcpcb"]:
                r = client.get("/v1/search", params={"supplier": name, "mpn": "X"}, headers=_auth_header())
                assert r.json()["status"] == "ok", f"Failed for supplier name: {name}"


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class TestDetail:
    @patch("supply_chain_monkey.routers.detail.create_supplier")
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

    @patch("supply_chain_monkey.routers.detail.create_supplier")
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
