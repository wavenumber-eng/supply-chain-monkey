"""
JLCPCB Supplier Implementation

Search remains scraper-backed because a public keyword/MPN search API is still
not confirmed. Detail lookup now uses a hybrid model:

- default: official OpenAPI detail lookup with scraper enrichment/fallback
- legacy option: force the old scraper-only detail path
"""

from __future__ import annotations

import logging
from typing import Any

from .jlc_openapi import JLCOpenAPIClient, detail_url_for_code
from .base import SupplierInterface, SupplierPartInfo, SupplierType, resolve_stock
from .jlc_scraper import JLCPartInfo, get_jlcpcb_part_details, search_jlcpcb_by_mpn

log = logging.getLogger(__name__)

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


class JLCPCBSupplier(SupplierInterface):
    """
    JLCPCB supplier adapter.

    Current split:
    - MPN search: website scraper
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

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search JLCPCB for parts matching an MPN.

        This remains scraper-backed because no official search-by-MPN endpoint
        has been confirmed yet.
        """
        try:
            verify = kwargs.get("verify_parts", True)
            max_results = kwargs.get("max_results", 0)
            jlc_results = search_jlcpcb_by_mpn(manufacturer_part_number, verify_parts=verify, max_results=max_results)
            return [self._convert_scraper_part(jlc_part) for jlc_part in jlc_results]
        except Exception as exc:
            log.info(f"Error searching JLCPCB for {manufacturer_part_number}: {exc}")
            return []

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
        enrich_with_scraper = kwargs.get("enrich_with_scraper", detail_backend == DETAIL_BACKEND_HYBRID)

        if detail_backend in {DETAIL_BACKEND_HYBRID, DETAIL_BACKEND_API} and self.api_client.is_configured():
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

    def _convert_scraper_part(
        self,
        jlc_part: JLCPartInfo,
        *,
        detail_backend: str = DETAIL_BACKEND_SCRAPER,
    ) -> SupplierPartInfo:
        stock_qty, stock_status = resolve_stock(jlc_part.stock)
        return SupplierPartInfo(
            supplier=SupplierType.JLCPCB,
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
            (scraper_part.manufacturer if scraper_part else "")
            or self._extract_manufacturer_from_parameters(detail)
        )
        description = str(detail.get("description") or (scraper_part.description if scraper_part else ""))
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


def search_jlcpcb(manufacturer_part_number: str, verify_parts: bool = True) -> list[SupplierPartInfo]:
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
