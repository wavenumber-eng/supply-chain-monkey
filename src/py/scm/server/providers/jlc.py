"""
JLCPCB Supplier Implementation

Search uses the public JLCPCB endpoint, LCSC shared C-code resolution, and a
legacy scraper fallback. Detail lookup uses a hybrid model:

- default: official OpenAPI detail lookup with scraper enrichment/fallback
- legacy option: force the old scraper-only detail path
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from scm.models import SupplierCapabilities

from .jlc_openapi import (
    JLC_COMPONENT_DETAIL_BATCH_LIMIT,
    JLCOpenAPIClient,
    detail_url_for_code,
)
from .base import SupplierInterface, SupplierPartInfo, SupplierType, resolve_stock
from .jlc_scraper import JLCPartInfo, get_jlcpcb_part_details, search_jlcpcb_by_mpn
from .lcsc_api import search_lcsc

log = logging.getLogger(__name__)

JLC_PUBLIC_SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-smt-component-order-platform"
    "/v1/overseasSmtComponentOrder/componentSearch/selectSmtComponentList"
)
JLC_PUBLIC_SEARCH_TIMEOUT_SECONDS = 15

_JLC_PUBLIC_SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Content-Type": "application/json",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts/componentsearch",
    "x-jlc-platform": "desktop",
}

DETAIL_BACKEND_HYBRID = "hybrid"
DETAIL_BACKEND_API = "api"
DETAIL_BACKEND_SCRAPER = "scraper"
DETAIL_BACKEND_LEGACY = "legacy_scraper"
VALID_DETAIL_BACKENDS = {
    DETAIL_BACKEND_HYBRID,
    DETAIL_BACKEND_API,
    DETAIL_BACKEND_SCRAPER,
    DETAIL_BACKEND_LEGACY,
    "legacy",
    "auto",
}


def _normalize_token(value: str) -> str:
    return value.upper().replace("-", "").replace(" ", "")


def _matches_expected_mpn(actual_mpn: str, expected_mpn: str) -> bool:
    if not expected_mpn:
        return True
    if not actual_mpn:
        return False
    return _normalize_token(actual_mpn) == _normalize_token(expected_mpn)


def _matches_search_keyword(actual_mpn: str, keyword: str) -> bool:
    actual = _normalize_token(actual_mpn)
    expected = _normalize_token(keyword)
    return bool(actual and expected and (actual == expected or expected in actual))


def _price_breaks_from_api(detail: dict[str, Any]) -> list[dict[str, Any]]:
    price_breaks: list[dict[str, Any]] = []
    for row in detail.get("priceRanges") or []:
        try:
            qty = int(row.get("startQuantity"))
            price = float(row.get("unitPrice"))
        except (TypeError, ValueError):
            continue
        price_breaks.append({"qty": qty, "unit_price": price, "currency": "USD"})
    return price_breaks


def _price_breaks_from_public_search(item: dict[str, Any]) -> list[dict[str, Any]]:
    price_breaks: list[dict[str, Any]] = []
    for row in item.get("componentPrices") or []:
        try:
            qty = int(row.get("startNumber"))
            price = float(row.get("productPrice"))
        except (TypeError, ValueError):
            continue
        price_breaks.append({"qty": qty, "unit_price": price, "currency": "USD"})
    return price_breaks


class JLCPCBSupplier(SupplierInterface):
    """
    JLCPCB supplier adapter.

    Current split:
    - MPN search: public website component-search API with scraper fallback
    - detail by C-code: official API by default, legacy scraper optionally
    """

    def __init__(self, **credentials):
        super().__init__(**credentials)

        self.detail_backend = self._normalize_detail_backend(
            credentials.get("detail_backend", DETAIL_BACKEND_HYBRID)
        )
        self.api_client = JLCOpenAPIClient(
            app_id=credentials.get("app_id"),
            access_key=credentials.get("access_key"),
            secret_key=credentials.get("secret_key"),
        )

    @property
    def supplier_type(self) -> SupplierType:
        return SupplierType.JLCPCB

    @property
    def parameter_field_name(self) -> str:
        return "JLCPCB Part #"

    @property
    def capabilities(self) -> SupplierCapabilities:
        api_batch_available = self.api_client.is_configured() and self.detail_backend in {
            DETAIL_BACKEND_HYBRID,
            DETAIL_BACKEND_API,
        }
        return SupplierCapabilities(
            supplier=self.supplier_type.value,
            supports_mpn_search=True,
            supports_spn_lookup=True,
            supports_native_spn_batch=api_batch_available,
            max_spn_batch_size=JLC_COMPONENT_DETAIL_BATCH_LIMIT if api_batch_available else 1,
            usage_unit="requests",
            notes=[
                "MPN search uses JLCPCB public search, LCSC shared C-code resolution, then scraper fallback.",
                "Native SPN batch uses JLC OpenAPI getComponentDetailByCode.",
            ],
        )

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search JLCPCB for parts matching an MPN.

        Public website search is tried first. LCSC resolves shared C-codes
        when that surface is empty or unavailable, followed by the legacy
        scraper as a final fallback.
        """
        verify = kwargs.get("verify_parts", True)
        max_results = kwargs.get("max_results", 0)
        public_results: list[SupplierPartInfo] | None = None
        try:
            public_results = self._search_public_component_api(
                manufacturer_part_number,
                verify_parts=verify,
                max_results=max_results,
                presale_type=kwargs.get("presale_type", "stock"),
            )
            if public_results:
                return public_results
        except Exception as exc:
            log.info(
                "JLCPCB public search failed for %s; falling back to scraper: %s",
                manufacturer_part_number,
                exc,
            )

        lcsc_results = self._search_via_lcsc_component_codes(
            manufacturer_part_number,
            verify_parts=verify,
            max_results=max_results,
        )
        if lcsc_results:
            return lcsc_results
        if public_results == []:
            return []

        try:
            jlc_results = search_jlcpcb_by_mpn(
                manufacturer_part_number, verify_parts=verify, max_results=max_results
            )
            return [self._convert_scraper_part(jlc_part) for jlc_part in jlc_results]
        except Exception as exc:
            log.info(f"Error searching JLCPCB for {manufacturer_part_number}: {exc}")
            return []

    def _search_via_lcsc_component_codes(
        self,
        keyword: str,
        *,
        verify_parts: bool,
        max_results: int,
    ) -> list[SupplierPartInfo]:
        page_size = max_results if max_results > 0 else 10
        try:
            products = search_lcsc(keyword, page_size=page_size)
        except Exception as exc:
            log.info("LCSC C-code resolution failed for JLCPCB search %s: %s", keyword, exc)
            return []

        results = []
        seen_codes = set()
        for product in products:
            if verify_parts and not _matches_search_keyword(product.product_model, keyword):
                continue
            if not product.product_code or product.product_code in seen_codes:
                continue
            seen_codes.add(product.product_code)
            part = self.get_part_details(
                product.product_code,
                expected_mpn=product.product_model,
            )
            if part is None:
                continue
            part.extra_data.update(
                {
                    "search_backend": "lcsc_c_code_resolution",
                    "lcsc_search_backend": product.search_backend,
                    "lcsc_product_url": product.product_url,
                    "lcsc_vendor_code": product.vendor_code,
                    "lcsc_product_source": product.product_source,
                }
            )
            results.append(part)
            if max_results > 0 and len(results) >= max_results:
                break
        return results

    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """
        Get JLC part details for a C-code.

        Supported detail backends:
        - hybrid (default): official API, enriched/fallback to scraper
        - api: official API only
        - scraper / legacy_scraper: old scraper-only detail path
        """
        expected_mpn = kwargs.get("expected_mpn", "")
        detail_backend = self._resolve_detail_backend(kwargs)
        enrich_with_scraper = kwargs.get(
            "enrich_with_scraper", detail_backend == DETAIL_BACKEND_HYBRID
        )

        if (
            detail_backend in {DETAIL_BACKEND_HYBRID, DETAIL_BACKEND_API}
            and self.api_client.is_configured()
        ):
            try:
                api_detail = self.api_client.get_component_detail_by_code(supplier_part_number)
                if api_detail:
                    api_mpn = str(api_detail.get("componentModel") or "")
                    if expected_mpn and not _matches_expected_mpn(api_mpn, expected_mpn):
                        return None

                    scraper_part = None
                    if enrich_with_scraper:
                        scraper_part = self._get_scraper_part(supplier_part_number)

                    return self._convert_api_detail(
                        api_detail,
                        scraper_part=scraper_part,
                        detail_backend=detail_backend,
                    )
            except Exception as exc:
                log.info(
                    "JLCPCB official detail lookup failed for %s via %s backend: %s",
                    supplier_part_number,
                    detail_backend,
                    exc,
                )
                if detail_backend == DETAIL_BACKEND_API:
                    return None

        if detail_backend in {DETAIL_BACKEND_HYBRID, DETAIL_BACKEND_SCRAPER, DETAIL_BACKEND_LEGACY}:
            return self._get_part_details_via_scraper(
                supplier_part_number,
                expected_mpn=expected_mpn,
                detail_backend=detail_backend,
            )

        log.info("Unknown JLCPCB detail backend %r; using scraper fallback.", detail_backend)
        return self._get_part_details_via_scraper(
            supplier_part_number,
            expected_mpn=expected_mpn,
            detail_backend=DETAIL_BACKEND_SCRAPER,
        )

    def get_part_details_batch(
        self, supplier_part_numbers: list[str], **kwargs
    ) -> dict[str, SupplierPartInfo | None]:
        """Get JLC component details for a batch of C-codes."""
        cleaned_codes = [code.strip() for code in supplier_part_numbers if code and code.strip()]
        results: dict[str, SupplierPartInfo | None] = {code: None for code in cleaned_codes}
        if not cleaned_codes:
            return results

        detail_backend = self._resolve_detail_backend(kwargs)
        if (
            detail_backend in {DETAIL_BACKEND_HYBRID, DETAIL_BACKEND_API}
            and self.api_client.is_configured()
        ):
            try:
                for start in range(0, len(cleaned_codes), JLC_COMPONENT_DETAIL_BATCH_LIMIT):
                    chunk = cleaned_codes[start : start + JLC_COMPONENT_DETAIL_BATCH_LIMIT]
                    for api_detail in self.api_client.get_component_detail_by_codes(chunk):
                        part = self._convert_api_detail(
                            api_detail,
                            scraper_part=None,
                            detail_backend=DETAIL_BACKEND_API,
                        )
                        if part.supplier_part_number:
                            results[part.supplier_part_number] = part
            except Exception as exc:
                log.info("JLCPCB official batch detail lookup failed: %s", exc)
                if detail_backend == DETAIL_BACKEND_API:
                    return results

            if detail_backend == DETAIL_BACKEND_API or all(
                results[code] is not None for code in cleaned_codes
            ):
                return results

        if detail_backend == DETAIL_BACKEND_HYBRID:
            missing_codes = [code for code in cleaned_codes if results[code] is None]
            for code in missing_codes:
                results[code] = self._get_part_details_via_scraper(
                    code,
                    expected_mpn="",
                    detail_backend=DETAIL_BACKEND_SCRAPER,
                )
            return results

        return super().get_part_details_batch(cleaned_codes, **kwargs)

    def validate_credentials(self) -> bool:
        try:
            if self.api_client.is_configured():
                return self.get_part_details("C2040", detail_backend=DETAIL_BACKEND_API) is not None
            return self.get_part_details("C2040", detail_backend=DETAIL_BACKEND_SCRAPER) is not None
        except Exception:
            return False

    def _resolve_detail_backend(self, kwargs: dict[str, Any]) -> str:
        if kwargs.get("use_legacy_detail_scraper"):
            return DETAIL_BACKEND_LEGACY
        return self._normalize_detail_backend(kwargs.get("detail_backend", self.detail_backend))

    def _normalize_detail_backend(self, backend: Any) -> str:
        text = str(backend or DETAIL_BACKEND_HYBRID).strip().lower()
        if text == "auto":
            return DETAIL_BACKEND_HYBRID
        if text == "legacy":
            return DETAIL_BACKEND_LEGACY
        if text in VALID_DETAIL_BACKENDS:
            return text
        log.info("Unknown JLCPCB detail backend %r; defaulting to hybrid.", backend)
        return DETAIL_BACKEND_HYBRID

    def _get_scraper_part(self, supplier_part_number: str) -> JLCPartInfo | None:
        return get_jlcpcb_part_details(supplier_part_number, expected_mpn="")

    def _get_part_details_via_scraper(
        self,
        supplier_part_number: str,
        *,
        expected_mpn: str = "",
        detail_backend: str,
    ) -> SupplierPartInfo | None:
        try:
            jlc_part = get_jlcpcb_part_details(supplier_part_number, expected_mpn=expected_mpn)
            if not jlc_part:
                return None
            return self._convert_scraper_part(jlc_part, detail_backend=detail_backend)
        except Exception as exc:
            log.info(f"Error getting JLCPCB scraper details for {supplier_part_number}: {exc}")
            return None

    def _search_public_component_api(
        self,
        keyword: str,
        *,
        verify_parts: bool,
        max_results: int,
        presale_type: str | None,
    ) -> list[SupplierPartInfo] | None:
        page_size = max_results if max_results and max_results > 0 else 25
        page_size = max(1, min(page_size, 100))
        body = {
            "currentPage": 1,
            "pageSize": page_size,
            "presaleType": presale_type,
            "searchType": 2,
            "keyword": keyword,
            "componentLibraryType": None,
            "stockFlag": False,
            "stockSort": None,
            "firstSortName": None,
            "secondSortName": None,
            "componentBrandList": [],
            "searchSource": "search",
            "componentSpecificationList": [],
            "componentAttributeList": [],
            "paramList": [],
            "startStockNumber": None,
        }

        response = requests.post(
            JLC_PUBLIC_SEARCH_URL,
            json=body,
            headers=_JLC_PUBLIC_SEARCH_HEADERS,
            timeout=JLC_PUBLIC_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 200:
            log.info(
                "JLCPCB public search returned code=%s msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return None

        page_info = (data.get("data") or {}).get("componentPageInfo") or {}
        parts = []
        for item in page_info.get("list") or []:
            part = self._convert_public_search_part(item)
            if verify_parts and not _matches_expected_mpn(
                str(part.manufacturer_part_number or ""), keyword
            ):
                continue
            parts.append(part)
            if max_results and len(parts) >= max_results:
                break
        return parts

    def _convert_public_search_part(self, item: dict[str, Any]) -> SupplierPartInfo:
        component_code = str(item.get("componentCode") or "")
        stock_qty, stock_status = resolve_stock(item.get("stockCount"))
        url_suffix = str(item.get("urlSuffix") or "").strip()
        product_url = (
            f"https://jlcpcb.com/partdetail/{url_suffix}"
            if url_suffix
            else detail_url_for_code(component_code)
        )

        return SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
            source_provider="jlcpcb",
            supplier_part_number=component_code,
            manufacturer=str(item.get("componentBrandEn") or ""),
            manufacturer_part_number=str(item.get("componentModelEn") or ""),
            description=str(item.get("describe") or item.get("componentName") or ""),
            datasheet_url=str(
                item.get("dataManualOfficialLink")
                or item.get("dataManualUrl")
                or item.get("dataManualFileAccessIdUrl")
                or ""
            ),
            product_url=product_url,
            stock_quantity=stock_qty,
            stock_status=stock_status,
            price_breaks=_price_breaks_from_public_search(item),
            lifecycle_status="",
            extra_data={
                "search_backend": "public_component_api",
                "public_search": item,
            },
        )

    def _convert_scraper_part(
        self,
        jlc_part: JLCPartInfo,
        *,
        detail_backend: str = DETAIL_BACKEND_SCRAPER,
    ) -> SupplierPartInfo:
        stock_qty, stock_status = resolve_stock(jlc_part.stock)
        return SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
            source_provider="jlcpcb",
            supplier_part_number=jlc_part.jlcpcb_code,
            manufacturer=jlc_part.manufacturer,
            manufacturer_part_number=jlc_part.mpn,
            description=jlc_part.description,
            product_url=jlc_part.url,
            stock_quantity=stock_qty,
            stock_status=stock_status,
            datasheet_url="",
            price_breaks=[],
            lifecycle_status="",
            extra_data={
                "detail_backend": detail_backend,
                "legacy_scraper": jlc_part.to_dict(),
            },
        )

    def _convert_api_detail(
        self,
        detail: dict[str, Any],
        *,
        scraper_part: JLCPartInfo | None,
        detail_backend: str,
    ) -> SupplierPartInfo:
        component_code = str(detail.get("componentCode") or "")
        manufacturer_part_number = str(detail.get("componentModel") or "")
        manufacturer = (
            scraper_part.manufacturer if scraper_part else ""
        ) or self._extract_manufacturer_from_parameters(detail)
        description = str(
            detail.get("description") or (scraper_part.description if scraper_part else "")
        )
        datasheet_url = str(detail.get("datasheetUrl") or detail.get("dataManualUrl") or "")
        stock_qty, stock_status = resolve_stock(detail.get("stockCount"))
        product_url = detail_url_for_code(component_code)

        extra_data: dict[str, Any] = {
            "detail_backend": detail_backend,
            "api_detail": detail,
        }
        if scraper_part:
            extra_data["legacy_scraper"] = scraper_part.to_dict()

        return SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
            source_provider="jlcpcb",
            supplier_part_number=component_code,
            manufacturer=manufacturer,
            manufacturer_part_number=manufacturer_part_number,
            description=description,
            datasheet_url=datasheet_url,
            product_url=product_url,
            stock_quantity=stock_qty,
            stock_status=stock_status,
            price_breaks=_price_breaks_from_api(detail),
            lifecycle_status="",
            extra_data=extra_data,
        )

    @staticmethod
    def _extract_manufacturer_from_parameters(detail: dict[str, Any]) -> str:
        for entry in detail.get("parameters") or []:
            name = str(entry.get("parameterName") or "").strip().lower()
            if name in {"manufacturer", "brand", "manufacturer name", "brand name"}:
                return str(entry.get("parameterValue") or "").strip()
        return ""


def search_jlcpcb(
    manufacturer_part_number: str, verify_parts: bool = True
) -> list[SupplierPartInfo]:
    jlc = JLCPCBSupplier()
    return jlc.search_by_mpn(manufacturer_part_number, verify_parts=verify_parts)


if __name__ == "__main__":
    log.info("=== JLCPCB Supplier Test ===\n")

    jlc = JLCPCBSupplier()

    log.info("1. Validating JLCPCB access...")
    if jlc.validate_credentials():
        log.info("   [OK] JLCPCB detail lookup is accessible\n")
    else:
        log.info("   [ERROR] Cannot access JLCPCB detail lookup\n")

    test_mpn = "GCM1555C1H100FA16D"
    log.info(f"2. Searching for MPN: {test_mpn}")
    results = jlc.search_by_mpn(test_mpn)
    log.info(f"   Found {len(results)} results:")
    for part in results:
        log.info(f"   - {part.supplier_part_number}: {part.description}")
        log.info(f"     Stock: {part.stock_quantity}")
    log.info("")

    test_c_code = "C2040"
    log.info(f"3. Getting hybrid details for C code: {test_c_code}")
    part = jlc.get_part_details(test_c_code)
    if part:
        log.info(f"   Supplier Part #: {part.supplier_part_number}")
        log.info(f"   MPN: {part.manufacturer_part_number}")
        log.info(f"   Description: {part.description}")
        log.info(f"   Stock: {part.stock_quantity}")
        log.info(f"   URL: {part.product_url}")
        log.info(f"   Backend: {part.extra_data.get('detail_backend')}")
    else:
        log.info("   [ERROR] Part not found")
    log.info("")

    log.info(f"4. Parameter field name: {jlc.parameter_field_name}")
    log.info("   (This should stay stable for downstream consumers)")
