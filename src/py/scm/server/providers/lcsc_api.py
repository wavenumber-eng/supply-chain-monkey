"""
LCSC internal JSON API client.

Uses the primary and third-party endpoints that the LCSC website frontend calls.
No API key required — these are public endpoints behind wmsc.lcsc.com.
"""

import logging
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)

LCSC_API_BASE = "https://wmsc.lcsc.com"
LCSC_SEARCH_PATH = "/ftps/wm/search/v3/global"
LCSC_THIRD_PARTY_SEARCH_PATH = "/ftps/wm/search/third"
LCSC_DETAIL_PATH = "/ftps/wm/product/detail"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.lcsc.com/",
    "Origin": "https://www.lcsc.com",
    "Content-Type": "application/json",
}


@dataclass
class LCSCProduct:
    """Parsed product from the LCSC API."""

    product_code: str  # e.g. "C2940195"
    product_model: str  # MPN
    brand: str
    description: str
    stock: int | str  # may be non-numeric in edge cases
    datasheet_url: str
    price_breaks: list[dict[str, Any]]
    lifecycle: str
    package: str
    packaging: str
    product_url: str
    search_backend: str = "lcsc_primary"
    vendor_code: str = ""
    product_source: str = ""


def search_lcsc(keyword: str, page: int = 1, page_size: int = 25) -> list[LCSCProduct]:
    """Search LCSC by keyword (MPN, description, etc.)."""
    page_size = max(1, min(page_size, 100))
    result = _post_search(
        LCSC_SEARCH_PATH,
        {"keyword": keyword, "currentPage": page, "pageSize": page_size},
    )
    search_vo = result.get("productSearchResultVO") or {}
    product_list = list(search_vo.get("productList") or [])
    if not product_list:
        product_list = list(result.get("exactMatchResult") or [])
    if not product_list and isinstance(result.get("tipProductDetailUrlVO"), dict):
        product_list = [result["tipProductDetailUrlVO"]]
    search_backend = "lcsc_primary"

    if not product_list:
        third_party = _post_search(
            LCSC_THIRD_PARTY_SEARCH_PATH,
            {"keyword": keyword, "currentPage": page, "pageSize": page_size},
        )
        product_list = list(third_party.get("productList") or [])
        search_backend = "lcsc_third_party"

    products = [_parse_product(item, search_backend=search_backend) for item in product_list]
    return _deduplicate_products(products)


def _post_search(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{LCSC_API_BASE}{path}"
    try:
        response = requests.post(url, json=body, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log.warning("[LCSC API] Search request failed for %s: %s", path, exc)
        return {}

    if data.get("code") != 200:
        log.warning(
            "[LCSC API] Search returned code=%s msg=%s for %s",
            data.get("code"),
            data.get("msg"),
            path,
        )
        return {}

    result = data.get("result")
    return result if isinstance(result, dict) else {}


def get_lcsc_detail(product_code: str) -> LCSCProduct | None:
    """Get full detail for a single LCSC product code."""
    url = f"{LCSC_API_BASE}{LCSC_DETAIL_PATH}"
    params = {"productCode": product_code}

    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.warning("[LCSC API] Detail request failed for %s: %s", product_code, exc)
        return None

    if data.get("code") != 200:
        log.warning("[LCSC API] Detail returned code=%s msg=%s", data.get("code"), data.get("msg"))
        return None

    item = data.get("result")
    if not item or not isinstance(item, dict):
        return None

    return _parse_product(item, search_backend="lcsc_detail")


def _parse_product(item: dict, *, search_backend: str = "lcsc_primary") -> LCSCProduct:
    """Convert a raw API item into an LCSCProduct."""
    product_code = item.get("productCode") or ""

    # Price breaks
    price_breaks = []
    for pb in item.get("productPriceList") or []:
        try:
            qty = int(pb.get("ladder", 0))
            price = float(
                pb.get("usdPrice") or pb.get("productPrice") or pb.get("currencyPrice") or 0
            )
            price_breaks.append({"qty": qty, "unit_price": price, "currency": "USD"})
        except (TypeError, ValueError):
            continue

    # Stock — prefer domesticStockVO.total, fall back to stockNumber
    stock_vo = item.get("domesticStockVO") or item.get("overseasStockVO") or {}
    stock = stock_vo.get("total") if isinstance(stock_vo, dict) else None
    if stock is None:
        stock = item.get("stockNumber", 0)

    # Lifecycle
    cycle = item.get("productCycle") or ""
    lifecycle = "Active" if cycle == "normal" else cycle

    product_url = item.get("url") or (
        f"https://www.lcsc.com/product-detail/{product_code}.html" if product_code else ""
    )

    return LCSCProduct(
        product_code=product_code,
        product_model=item.get("productCodeManufacturer") or item.get("productModel") or "",
        brand=item.get("brandNameEn") or "",
        description=(
            item.get("productIntroEn")
            or item.get("productCodeManufacturer")
            or item.get("productModel")
            or ""
        ),
        stock=stock,
        datasheet_url=item.get("pdfUrl") or "",
        price_breaks=price_breaks,
        lifecycle=lifecycle,
        package=item.get("encapStandard") or "",
        packaging=item.get("productArrange") or "",
        product_url=product_url,
        search_backend=search_backend,
        vendor_code=str(item.get("vendorCode") or ""),
        product_source=str(item.get("productSource") or ""),
    )


def _deduplicate_products(products: list[LCSCProduct]) -> list[LCSCProduct]:
    selected: dict[str, LCSCProduct] = {}
    order: list[str] = []
    for product in products:
        identity = product.product_code or f"{product.brand}\0{product.product_model}"
        if identity not in selected:
            selected[identity] = product
            order.append(identity)
            continue
        if _offer_rank(product) < _offer_rank(selected[identity]):
            selected[identity] = product
    return [selected[identity] for identity in order]


def _offer_rank(product: LCSCProduct) -> tuple[float, int, str]:
    prices = [
        float(row["unit_price"])
        for row in product.price_breaks
        if isinstance(row.get("unit_price"), int | float) and float(row["unit_price"]) > 0
    ]
    try:
        stock = int(product.stock)
    except (TypeError, ValueError):
        stock = 0
    return (min(prices, default=float("inf")), -stock, product.vendor_code)
