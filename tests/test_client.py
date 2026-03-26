"""Tests for the SCM client library.

Runs the client against the real server via TestClient (in-process, no network).
This validates the contract — the client deserializes what the server serializes.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from scm.server.main import app
from scm.server.providers.base import SupplierPartInfo
from scm.models import SupplierType, ServiceEnvelope, SUPPLIERS
from scm.client import SCMClient


class _InProcessClient(SCMClient):
    """SCMClient that uses FastAPI TestClient instead of real HTTP."""

    def __init__(self, test_client: TestClient, token: str):
        self._tc = test_client
        self.token = token
        self.timeout = 30.0
        self.url = ""

    def _get(self, path, params=None, headers=None):
        return self._tc.get(path, params=params, headers=headers)


# Override the requests.get calls to use TestClient
import requests as _requests


@pytest.fixture
def scm_client():
    """SCMClient wired to the FastAPI app in-process."""
    with patch("scm.server.auth.settings") as mock_settings:
        mock_settings.service_token = "test-token"
        tc = TestClient(app)

        # Patch requests.get in the client module to use TestClient
        original_get = _requests.get

        def mock_get(url, **kwargs):
            # Strip the base URL prefix (empty for in-process)
            path = url
            params = kwargs.get("params")
            headers = kwargs.get("headers")
            response = tc.get(path, params=params, headers=headers)
            return response

        with patch("scm.client.requests.get", side_effect=mock_get):
            yield SCMClient(url="", token="test-token")


def _mock_part():
    return SupplierPartInfo(
        supplier=SupplierType.JLCPCB,
        supplier_part_number="C2870085",
        manufacturer="Texas Instruments",
        manufacturer_part_number="TPS543620RPYR",
        description="Buck converter",
        stock_quantity=791,
        stock_status="in_stock",
        price_breaks=[{"qty": 1, "unit_price": 2.92, "currency": "USD"}],
        extra_data={"packaging": "Tape & Reel"},
    )


class TestClientHealth:
    def test_health(self, scm_client):
        result = scm_client.health()
        assert result["status"] == "ok"


class TestClientSearch:
    @patch("scm.server.routers.search.create_supplier")
    def test_search_returns_envelope(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part()]
        mock_create.return_value = mock_supplier

        result = scm_client.search("jlcpcb", "TPS543620RPYR")

        assert isinstance(result, ServiceEnvelope)
        assert result.status == "ok"
        assert result.supplier == "JLCPCB"
        assert result.parameter_field_name == "JLCPCB Part #"
        assert len(result.data) == 1
        assert result.data[0]["supplier_part_number"] == "C2870085"
        assert result.data[0]["packaging"] == "Tape & Reel"

    @patch("scm.server.routers.search.create_supplier")
    def test_search_not_found(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = []
        mock_create.return_value = mock_supplier

        result = scm_client.search("jlcpcb", "NONEXISTENT")
        assert result.status == "not_found"


class TestClientSearchAll:
    @patch("scm.server.routers.search.create_supplier")
    def test_search_all_returns_dict(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part()]
        mock_create.return_value = mock_supplier

        results = scm_client.search_all("TPS543620RPYR")

        assert isinstance(results, dict)
        for supplier_name in SUPPLIERS:
            assert supplier_name in results
            assert isinstance(results[supplier_name], ServiceEnvelope)

    @patch("scm.server.routers.search.create_supplier")
    def test_search_all_subset(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.search_by_mpn.return_value = [_mock_part()]
        mock_create.return_value = mock_supplier

        results = scm_client.search_all("TPS543620RPYR", suppliers=["jlcpcb", "lcsc"])

        assert len(results) == 2
        assert "jlcpcb" in results
        assert "lcsc" in results
        assert "digikey" not in results


class TestClientDetail:
    @patch("scm.server.routers.detail.create_supplier")
    def test_detail_returns_envelope(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.get_part_details.return_value = _mock_part()
        mock_create.return_value = mock_supplier

        result = scm_client.detail("jlcpcb", "C2870085")

        assert isinstance(result, ServiceEnvelope)
        assert result.status == "ok"
        assert result.data["supplier_part_number"] == "C2870085"


class TestClientEnumeration:
    def test_suppliers_available(self):
        """Consumers can enumerate suppliers from the contract."""
        assert len(SUPPLIERS) == 4
        assert "jlcpcb" in SUPPLIERS

    def test_supplier_type_enum(self):
        """Consumers can use SupplierType for type-safe references."""
        assert SupplierType.JLCPCB.value == "JLCPCB"
        assert SupplierType("JLCPCB") == SupplierType.JLCPCB
