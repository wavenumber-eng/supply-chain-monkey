"""
LCSC Parts Search and Scraper

LCSC (lcsc.com) is part of the JLC company family and uses the same C code numbering
system as JLCPCB. This scraper provides functions to search for parts on LCSC and
extract part details.

LCSC may have faster response times than JLCPCB for the same parts.

Example Usage:
    # Simple search by MPN
    >>> from supply_chain_monkey.lcsc_scraper import search_lcsc_by_mpn
    >>> results = search_lcsc_by_mpn("TPS543620RPYR")
    >>> for part in results:
    ...     log.info(f"{part.lcsc_code}: {part.description}")

    # Get details for a specific C code
    >>> from supply_chain_monkey.lcsc_scraper import get_lcsc_part_details
    >>> part = get_lcsc_part_details("C2870085")
    >>> log.info(part.description)
"""

import logging
import re
from urllib.parse import quote_plus

import requests

log = logging.getLogger(__name__)


class LCSCPartInfo:
    """Container for LCSC part information"""
    def __init__(self, lcsc_code: str, mpn: str = "", description: str = "", url: str = "", stock: int = 0, manufacturer: str = ""):
        self.lcsc_code = lcsc_code  # C code (same as JLCPCB)
        self.mpn = mpn
        self.description = description
        self.url = url
        self.stock = stock
        self.manufacturer = manufacturer

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'lcsc_code': self.lcsc_code,
            'mpn': self.mpn,
            'description': self.description,
            'url': self.url,
            'stock': self.stock,
            'manufacturer': self.manufacturer
        }

    def __repr__(self):
        return f"LCSCPartInfo({self.lcsc_code}, {self.mpn}, stock={self.stock}, {self.description[:30]}...)"


def search_lcsc_by_mpn(mpn: str, verify_parts: bool = True) -> list[LCSCPartInfo]:
    """
    Search LCSC for parts matching a manufacturer part number.

    Args:
        mpn: Manufacturer Part Number to search for
        verify_parts: If True, verify each C code by fetching detail page

    Returns:
        List of LCSCPartInfo objects for matching parts
    """
    # LCSC search URL - includes the MPN in both query and search zone
    search_url = f"https://www.lcsc.com/search?q={quote_plus(mpn)}&s_z=n_{quote_plus(mpn)}"

    try:
        log.info(f"[LCSC] Searching for MPN: {mpn}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Extract C codes from HTML (C codes can be 4-9 digits)
        c_code_pattern = r'C\d{4,9}'
        all_c_codes = re.findall(c_code_pattern, response.text)
        unique_c_codes = list(set(all_c_codes))

        log.info(f"[LCSC] Found {len(unique_c_codes)} potential C codes in search results")

        results = []

        if verify_parts:
            # Verify each C code by fetching its detail page
            log.info(f"[LCSC] Verifying {len(unique_c_codes)} C codes...")
            for i, c_code in enumerate(unique_c_codes, 1):
                log.info(f"[LCSC] Checking {c_code} ({i}/{len(unique_c_codes)})...")
                part_info = get_lcsc_part_details(c_code, expected_mpn=mpn)
                if part_info:
                    log.info(f"[LCSC] Validated: {c_code} - {part_info.mpn}")
                    results.append(part_info)
                else:
                    log.info(f"[LCSC] Rejected: {c_code} (MPN mismatch or error)")
        else:
            # Return unverified results
            for c_code in unique_c_codes:
                results.append(LCSCPartInfo(
                    lcsc_code=c_code,
                    mpn=mpn,
                    url=f"https://www.lcsc.com/product-detail/{c_code}.html"
                ))

        # If regex method found nothing, try Claude as fallback
        if not results:
            log.info("[LCSC] No valid parts found with regex, trying Claude AI fallback...")
            try:
                from .claude_scraper_helper import find_c_code_with_claude

                c_code = find_c_code_with_claude(response.text, mpn, supplier="LCSC")
                if c_code:
                    log.info(f"[LCSC] Claude found C code: {c_code}")
                    # Verify the C code Claude found
                    part_info = get_lcsc_part_details(c_code, expected_mpn=mpn)
                    if part_info:
                        results.append(part_info)
                        log.info(f"[LCSC] Claude successfully found {c_code} for {mpn}")
                    else:
                        log.warning(f"[LCSC] Claude found {c_code} but validation failed")
                else:
                    log.info("[LCSC] Claude could not find matching C code")
            except ImportError:
                log.warning("[LCSC] Claude helper not available (missing anthropic package)")
            except Exception as e:
                log.error(f"[LCSC] Claude fallback error: {str(e)}")

        if results:
            log.info(f"[LCSC] Search complete: Found {len(results)} valid part(s)")
        else:
            log.warning(f"[LCSC] No parts found for {mpn}")

        return results

    except Exception as e:
        log.error(f"[LCSC] Error searching for {mpn}: {str(e)}")
        return []


def get_lcsc_part_details(c_code: str, expected_mpn: str = "") -> LCSCPartInfo | None:
    """
    Get detailed information for an LCSC part by its C code.

    Args:
        c_code: LCSC part number (e.g., C2870085)
        expected_mpn: Expected manufacturer part number (for validation)

    Returns:
        LCSCPartInfo object if successful, None otherwise
    """
    # LCSC detail URL
    detail_url = f"https://www.lcsc.com/product-detail/{c_code}.html"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

        response = requests.get(detail_url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        # Extract MPN from the detail page
        found_mpn = _extract_mpn(response.text, expected_mpn)

        # If we have an expected MPN and the found MPN doesn't match, reject this part
        if expected_mpn and found_mpn:
            # Normalize for comparison (case-insensitive, remove whitespace/hyphens)
            expected_normalized = expected_mpn.upper().replace("-", "").replace(" ", "")
            found_normalized = found_mpn.upper().replace("-", "").replace(" ", "")

            if expected_normalized != found_normalized:
                # This C code is for a different part - reject it
                return None

        # Extract description
        description = _extract_description(response.text)

        # Extract stock
        stock = _extract_stock(response.text)

        # Extract manufacturer
        manufacturer = _extract_manufacturer(response.text)

        return LCSCPartInfo(
            lcsc_code=c_code,
            mpn=found_mpn or expected_mpn,
            description=description,
            url=detail_url,
            stock=stock,
            manufacturer=manufacturer
        )

    except Exception as e:
        log.info(f"Error getting details for {c_code}: {str(e)}")
        return None


def _extract_manufacturer(html_text: str) -> str:
    """
    Extract manufacturer name from LCSC detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Extracted manufacturer name or empty string
    """
    # Try title tag first: "NRF52840-QIAA-R | NORDIC | Price | In Stock | LCSC Electronics"
    title_match = re.search(r'<title>([^<]+)</title>', html_text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1)
        parts = [p.strip() for p in title.split('|')]
        # Manufacturer is typically the second part
        if len(parts) >= 2 and parts[1] and parts[1].upper() not in ['PRICE', 'IN STOCK', 'LCSC', 'LCSC ELECTRONICS']:
            return parts[1]

    # Try JavaScript object patterns
    manufacturer_patterns = [
        r'"brand":\s*"([^"]+)"',
        r'"manufacturer":\s*"([^"]+)"',
        r'brand:\s*"([^"]+)"',
        r'manufacturer:\s*"([^"]+)"',
        r'Mfr\.:\s*<[^>]*>([^<]+)<',
    ]

    for pattern in manufacturer_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            manufacturer = match.group(1).strip()
            # Skip generic or placeholder values
            if manufacturer and manufacturer.upper() not in ['MANUFACTURER', 'BRAND', 'N/A', 'UNKNOWN', 'MFR']:
                return manufacturer

    return ""


def _extract_mpn(html_text: str, expected_mpn: str = "") -> str | None:
    """
    Extract manufacturer part number from LCSC detail page HTML.

    Args:
        html_text: HTML content from detail page
        expected_mpn: Expected MPN to look for

    Returns:
        Extracted MPN or None
    """
    mpn_patterns = [
        rf'{re.escape(expected_mpn)}' if expected_mpn else None,  # Exact match
        r'Mfr\.Part.*?[:：]\s*([A-Z0-9\-_]+)',  # Mfr.Part field
        r'MFR\.Part.*?[:：]\s*([A-Z0-9\-_]+)',  # MFR.Part field
        r'Model.*?[:：]\s*([A-Z0-9\-_]+)',  # Model field
    ]

    for pattern in mpn_patterns:
        if pattern is None:
            continue
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            if pattern == rf'{re.escape(expected_mpn)}':
                return match.group(0)
            else:
                return match.group(1)

    return None


def _extract_description(html_text: str) -> str:
    """
    Extract part description from LCSC detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Extracted description or empty string
    """
    desc_patterns = [
        r'<title>([^<]+?)\s*-\s*LCSC',  # Page title
        r'"description"\s*:\s*"([^"]+)"',  # JSON metadata
        r'Description.*?[:：]\s*<[^>]*>([^<]+)<',  # Description field
        r'<h1[^>]*>([^<]+)</h1>',  # Main title
    ]

    for pattern in desc_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            description = match.group(1).strip()

            # Decode unicode escape sequences (e.g., \u002F -> /)
            description = _decode_unicode_escapes(description)

            # Clean up common noise
            description = description.replace('LCSC - ', '').replace(' - LCSC', '')

            return description

    return ""


def _decode_unicode_escapes(text: str) -> str:
    """
    Decode unicode escape sequences in JavaScript strings.

    Args:
        text: Text potentially containing unicode escapes like \u002F

    Returns:
        Decoded text
    """
    def replace_unicode(match):
        return chr(int(match.group(1), 16))

    return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)


def _extract_stock(html_text: str) -> int:
    """
    Extract stock quantity from LCSC detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Stock quantity as integer, or 0 if not found
    """
    stock_patterns = [
        r'"stock"\s*:\s*(\d+)',  # JSON stock field
        r'stock.*?[:：]\s*(\d+)',  # stock label (case insensitive)
        r'Stock.*?[:：]\s*(\d+)',  # Stock label
        r'Inventory.*?[:：]\s*(\d+)',  # Inventory label
        r'>(\d+)\s*In\s*Stock<',  # "X In Stock" text
        r'available.*?[:：]\s*(\d+)',  # Available quantity
    ]

    for pattern in stock_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            try:
                stock_value = int(match.group(1))
                return stock_value
            except (ValueError, IndexError):
                continue

    return 0


# Convenience function for backwards compatibility
def verify_lcsc_code(c_code: str, expected_mpn: str = "") -> dict | None:
    """
    Legacy function for backwards compatibility.

    Returns dictionary format instead of LCSCPartInfo object.
    """
    part_info = get_lcsc_part_details(c_code, expected_mpn)
    return part_info.to_dict() if part_info else None


def scrape_lcsc_search(mpn: str) -> list[dict]:
    """
    Legacy function for backwards compatibility.

    Returns list of dictionaries instead of LCSCPartInfo objects.
    """
    results = search_lcsc_by_mpn(mpn, verify_parts=True)
    return [part.to_dict() for part in results]


if __name__ == "__main__":
    # Example usage and testing
    log.info("=== LCSC Scraper Test ===\n")

    # Test 1: Search by MPN
    mpn = "TPS543620RPYR"
    log.info(f"Searching for MPN: {mpn}")
    results = search_lcsc_by_mpn(mpn)
    log.info(f"Found {len(results)} results:")
    for part in results:
        log.info(f"  {part.lcsc_code}: {part.description}")
    log.info()

    # Test 2: Get specific part details
    c_code = "C2870085"
    log.info(f"Getting details for C code: {c_code}")
    part = get_lcsc_part_details(c_code)
    if part:
        log.info(f"  MPN: {part.mpn}")
        log.info(f"  Description: {part.description}")
        log.info(f"  URL: {part.url}")
        log.info(f"  Stock: {part.stock}")
    else:
        log.info("  No details found")
