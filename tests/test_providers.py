"""Unit tests for provider utilities (no network calls)."""

from typing import Any, cast

from scm.server.providers.base import (
    SupplierInterface,
    SupplierPartInfo,
    get_default_supplier_capabilities,
    rate_limit_snapshot_from_headers,
    resolve_stock,
)
from scm.server.providers.digikey import DigikeySupplier
from scm.server.providers.jlc import JLCPCBSupplier
from scm.server.providers.jlc_openapi import JLCOpenAPIClient
from scm.models import SupplierType


class _JsonResponse:
    def __init__(self, data: dict[str, Any]):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._data


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


class _FakeSupplier(SupplierInterface):
    @property
    def supplier_type(self):
        return SupplierType.JLCPCB

    @property
    def parameter_field_name(self):
        return "JLCPCB Part #"

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs):
        return []

    def get_part_details(self, supplier_part_number: str, **kwargs):
        if supplier_part_number == "C1":
            return SupplierPartInfo(
                supplier=SupplierType.JLCPCB,
                source_provider="test",
                supplier_part_number="C1",
                manufacturer="Test",
                manufacturer_part_number="TEST1",
            )
        return None


class TestSupplierBatchDefaults:
    def test_default_batch_loops_single_details(self):
        supplier = _FakeSupplier()
        results = supplier.get_part_details_batch(["C1", "C404"])
        assert results["C1"] is not None
        assert results["C1"].supplier_part_number == "C1"
        assert results["C404"] is None

    def test_static_capabilities_include_digikey_quota_shape(self):
        capabilities = get_default_supplier_capabilities(SupplierType.DIGIKEY)
        assert capabilities.supports_spn_lookup is True
        assert capabilities.max_spn_batch_size == 1
        assert capabilities.rate_limit_per_day == 1000
        assert capabilities.supports_quota_headers is True


class TestRateLimitHeaders:
    def test_digikey_rate_limit_headers_parse(self):
        snapshot = rate_limit_snapshot_from_headers({
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "742",
            "X-BurstLimit-Limit": "120",
            "X-BurstLimit-Remaining": "119",
            "X-BurstLimit-Reset": "60",
            "Retry-After": "5",
        })

        assert snapshot is not None
        assert snapshot.request_limit == 1000
        assert snapshot.requests_remaining == 742
        assert snapshot.burst_limit == 120
        assert snapshot.burst_remaining == 119
        assert snapshot.reset_seconds == 60
        assert snapshot.retry_after_seconds == 5

    def test_unrelated_headers_return_none(self):
        assert rate_limit_snapshot_from_headers({"Content-Type": "application/json"}) is None


class TestJLCOpenAPIParsing:
    def test_detail_list_accepts_pdf_wrapper_shape(self):
        client = JLCOpenAPIClient(app_id="a", access_key="b", secret_key="c")

        def fake_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "data": {
                    "componentDetailResponseVOList": [
                        {"componentCode": "C1", "componentModel": "TEST1"}
                    ]
                }
            }

        cast(Any, client)._post = fake_post

        details = client.get_component_detail_by_codes(["C1"])

        assert details == [{"componentCode": "C1", "componentModel": "TEST1"}]


class TestJLCPublicSearchParsing:
    def test_search_by_mpn_uses_public_component_api(self, monkeypatch):
        from scm.server.providers import jlc as jlc_module

        def fake_post(
            url: str,
            json: dict[str, Any],
            headers: dict[str, str],
            timeout: int,
        ) -> _JsonResponse:
            assert url == jlc_module.JLC_PUBLIC_SEARCH_URL
            assert json["keyword"] == "TPS543620RPYR"
            return _JsonResponse({
                "code": 200,
                "data": {
                    "componentPageInfo": {
                        "list": [
                            {
                                "componentCode": "C2870085",
                                "componentBrandEn": "Texas Instruments",
                                "componentModelEn": "TPS543620RPYR",
                                "componentName": "TI TPS543620RPYR",
                                "describe": "Buck Switching Regulator",
                                "stockCount": 654,
                                "dataManualOfficialLink": "https://example.test/datasheet.pdf",
                                "urlSuffix": "TexasInstruments-TPS543620RPYR/C2870085",
                                "componentPrices": [
                                    {"startNumber": 1, "productPrice": 3.1027}
                                ],
                            }
                        ]
                    }
                },
            })

        monkeypatch.setattr(jlc_module.requests, "post", fake_post)

        supplier = JLCPCBSupplier()
        parts = supplier.search_by_mpn("TPS543620RPYR", max_results=1)

        assert len(parts) == 1
        part = parts[0]
        assert part.supplier_part_number == "C2870085"
        assert part.manufacturer == "Texas Instruments"
        assert part.manufacturer_part_number == "TPS543620RPYR"
        assert part.stock_quantity == 654
        assert part.price_breaks == [{"qty": 1, "unit_price": 3.1027, "currency": "USD"}]
        assert part.extra_data["search_backend"] == "public_component_api"

    def test_empty_public_component_api_response_does_not_fall_back_to_scraper(self, monkeypatch):
        from scm.server.providers import jlc as jlc_module

        def fake_post(
            url: str,
            json: dict[str, Any],
            headers: dict[str, str],
            timeout: int,
        ) -> _JsonResponse:
            return _JsonResponse({
                "code": 200,
                "data": {"componentPageInfo": {"total": 0, "list": []}},
            })

        def fail_scraper(*args, **kwargs):
            raise AssertionError("scraper fallback should not run after a valid empty response")

        monkeypatch.setattr(jlc_module.requests, "post", fake_post)
        monkeypatch.setattr(jlc_module, "search_jlcpcb_by_mpn", fail_scraper)

        supplier = JLCPCBSupplier()
        assert supplier.search_by_mpn("NONEXISTENT_PART_12345_XYZ", verify_parts=False) == []


class TestLCSCSearchParsing:
    def test_search_accepts_v3_exact_match_result(self, monkeypatch):
        from scm.server.providers import lcsc_api

        def fake_post(
            url: str,
            json: dict[str, Any],
            headers: dict[str, str],
            timeout: int,
        ) -> _JsonResponse:
            assert url.endswith("/ftps/wm/search/v3/global")
            assert json["keyword"] == "TPS543620RPYR"
            return _JsonResponse({
                "code": 200,
                "result": {
                    "productSearchResultVO": None,
                    "exactMatchResult": [
                        {
                            "productCode": "C2870085",
                            "productModel": "TPS543620RPYR",
                            "brandNameEn": "TI",
                            "productIntroEn": "Buck Switching Regulator",
                            "stockNumber": 654,
                            "productCycle": "normal",
                            "encapStandard": "VQFN-14-HR(2.5x3)",
                            "productArrange": "Tape & Reel (TR)",
                            "pdfUrl": "https://example.test/datasheet.pdf",
                            "url": "https://www.lcsc.com/product-detail/C2870085.html",
                            "productPriceList": [
                                {"ladder": 1, "usdPrice": 3.115}
                            ],
                        }
                    ],
                },
            })

        monkeypatch.setattr(lcsc_api.requests, "post", fake_post)

        products = lcsc_api.search_lcsc("TPS543620RPYR")

        assert len(products) == 1
        product = products[0]
        assert product.product_code == "C2870085"
        assert product.product_model == "TPS543620RPYR"
        assert product.brand == "TI"
        assert product.stock == 654
        assert product.price_breaks == [{"qty": 1, "unit_price": 3.115, "currency": "USD"}]


class TestDigikeyParsing:
    def test_get_part_details_unwraps_product_details_response(self):
        supplier = DigikeySupplier(client_id="id", client_secret="secret")

        def fake_make_request(
            url: str,
            method: str = "GET",
            json_data: dict[str, Any] | None = None,
            max_retries: int = 3,
        ) -> dict[str, Any] | None:
            return {
                "Product": {
                    "Manufacturer": {"Name": "Test Mfr"},
                    "ManufacturerProductNumber": "TEST1",
                    "Description": {"ProductDescription": "Test part"},
                    "QuantityAvailable": 10,
                    "ProductVariations": [
                        {
                            "DigiKeyProductNumber": "296-TEST1-ND",
                            "PackageType": {"Name": "Cut Tape"},
                        }
                    ],
                }
            }

        cast(Any, supplier)._make_request = fake_make_request

        part = supplier.get_part_details("296-TEST1-ND", expected_mpn="TEST1")

        assert part is not None
        assert part.supplier_part_number == "296-TEST1-ND"
        assert part.manufacturer_part_number == "TEST1"
        assert part.extra_data["packaging"] == "Cut Tape"

    def test_detail_list_accepts_sdk_list_shape(self):
        client = JLCOpenAPIClient(app_id="a", access_key="b", secret_key="c")

        def fake_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "data": [{"componentCode": "C1", "componentModel": "TEST1"}]
            }

        cast(Any, client)._post = fake_post

        details = client.get_component_detail_by_codes(["C1"])

        assert details == [{"componentCode": "C1", "componentModel": "TEST1"}]
