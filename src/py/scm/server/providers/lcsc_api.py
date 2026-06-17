"""
LCSC internal JSON API client.

Uses the same endpoints that the LCSC website frontend calls.
No API key required — these are public endpoints behind wmsc.lcsc.com.
"""

import logging
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)

LCSC_API_BASE = "https://wmsc.lcsc.com"
LCSC_SEARCH_PATH = "/ftps/wm/search/v3/global"
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


def search_lcsc(keyword: str, page: int = 1, page_size: int = 25) -> list[LCSCProduct]:
    """Search LCSC by keyword (MPN, description, etc.)."""
    url = f"{LCSC_API_BASE}{LCSC_SEARCH_PATH}"
    body = {"keyword": keyword, "currentPage": page, "pageSize": page_size}

    try:
        r = requests.post(url, json=body, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.warning("[LCSC API] Search request failed: %s", exc)
        return []

    if data.get("code") != 200:
        log.warning("[LCSC API] Search returned code=%s msg=%s", data.get("code"), data.get("msg"))
        return []

    result = data.get("result") or {}
    search_vo = result.get("productSearchResultVO") or {}
    product_list = list(search_vo.get("productList") or [])
    if not product_list:
        product_list = list(result.get("exactMatchResult") or [])
    if not product_list and isinstance(result.get("tipProductDetailUrlVO"), dict):
        product_list = [result["tipProductDetailUrlVO"]]

    products = []
    for item in product_list:
        products.append(_parse_product(item))
    return products


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

    return _parse_product(item)


def _parse_product(item: dict) -> LCSCProduct:
    """Convert a raw API item into an LCSCProduct."""
    product_code = item.get("productCode") or ""

    # Price breaks
    price_breaks = []
    for pb in item.get("productPriceList") or []:
        try:
            qty = int(pb.get("ladder", 0))
            price = float(pb.get("usdPrice") or pb.get("productPrice") or 0)
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
        product_model=item.get("productModel") or "",
        brand=item.get("brandNameEn") or "",
        description=item.get("productIntroEn") or "",
        stock=stock,
        datasheet_url=item.get("pdfUrl") or "",
        price_breaks=price_breaks,
        lifecycle=lifecycle,
        package=item.get("encapStandard") or "",
        packaging=item.get("productArrange") or "",
        product_url=product_url,
    )
