"""Tests for the SCM client library.

Runs the client against the real server via TestClient (in-process, no network).
This validates the contract — the client deserializes what the server serializes.
"""

from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from scm.client import SCMClient
from scm.models import (
    SUPPLIERS,
    RateLimitSnapshot,
    ServiceEnvelope,
    SupplierCapabilities,
    SupplierType,
)
from scm.server.main import app
from scm.server.providers.base import SupplierPartInfo


class _InProcessClient(SCMClient):
    """SCMClient that uses FastAPI TestClient instead of real HTTP."""

    def __init__(self, test_client: TestClient, token: str):
        self._tc = test_client
        self.token = token
        self.timeout = 30.0
        self.url = ""

    def _get(self, path, params=None, headers=None):
        return self._tc.get(path, params=params, headers=headers)


@pytest.fixture
def scm_client():
    """SCMClient wired to the FastAPI app in-process."""
    with patch("scm.server.auth.settings") as mock_settings:
        mock_settings.service_token = "test-token"
        tc = TestClient(app)

        def mock_get(url, **kwargs):
            # Strip the base URL prefix (empty for in-process)
            path = url
            params = kwargs.get("params")
            headers = kwargs.get("headers")
            response = tc.get(path, params=params, headers=headers)
            return response

        def mock_post(url, **kwargs):
            path = url
            json_body = kwargs.get("json")
            headers = kwargs.get("headers")
            response = tc.post(path, json=json_body, headers=headers)
            return response

        with (
            patch("scm.client.requests.get", side_effect=mock_get),
            patch("scm.client.requests.post", side_effect=mock_post),
        ):
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


class TestClientProviderStatus:
    def test_providers_status_returns_capabilities(self, scm_client):
        result = scm_client.providers_status()

        assert "providers" in result
        assert "JLCPCB" in result["providers"]
        assert result["providers"]["JLCPCB"]["capabilities"]["supports_spn_lookup"] is True


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


class TestClientSpn:
    @patch("scm.server.routers.spn.create_supplier")
    def test_spn_returns_envelope(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.capabilities = SupplierCapabilities(supplier="JLCPCB")
        mock_supplier.get_rate_limit_snapshot.return_value = RateLimitSnapshot(
            request_limit=1000,
            requests_remaining=999,
        )
        mock_supplier.get_part_details.return_value = _mock_part()
        mock_create.return_value = mock_supplier

        result = scm_client.spn("jlcpcb", "C2870085")

        assert isinstance(result, ServiceEnvelope)
        assert result.status == "ok"
        assert result.data["supplier_part_number"] == "C2870085"
        assert result.provider_capabilities is not None
        assert result.provider_capabilities.supports_spn_lookup is True
        assert result.rate_limit is not None
        assert result.rate_limit.requests_remaining == 999

    @patch("scm.server.routers.spn.create_supplier")
    def test_spn_batch_returns_envelope(self, mock_create, scm_client):
        mock_supplier = MagicMock()
        mock_supplier.capabilities = SupplierCapabilities(
            supplier="JLCPCB",
            supports_native_spn_batch=True,
            max_spn_batch_size=1000,
        )
        mock_supplier.get_rate_limit_snapshot.return_value = None
        mock_supplier.get_part_details_batch.return_value = {
            "C2870085": _mock_part(),
            "C404": None,
        }
        mock_create.return_value = mock_supplier

        result = scm_client.spn_batch("jlcpcb", ["C2870085", "C404"])

        assert isinstance(result, ServiceEnvelope)
        assert result.status == "partial"
        assert result.provider_capabilities is not None
        assert result.provider_capabilities.max_spn_batch_size == 1000
        assert result.data[0]["status"] == "ok"
        assert result.data[1]["status"] == "not_found"


class TestClientEnumeration:
    def test_suppliers_available(self):
        """Consumers can enumerate suppliers from the contract."""
        assert len(SUPPLIERS) == 4
        assert "jlcpcb" in SUPPLIERS

    def test_supplier_type_enum(self):
        """Consumers can use SupplierType for type-safe references."""
        assert SupplierType.JLCPCB.value == "JLCPCB"
        assert SupplierType("JLCPCB") == SupplierType.JLCPCB
