"""
JLCPCB Parts Search and Scraper
Provides functions to search for parts on JLCPCB and extract part details.

Example Usage:
    # Simple search by MPN
    >>> from supply_chain_monkey.jlc_scraper import search_jlcpcb_by_mpn
    >>> results = search_jlcpcb_by_mpn("GCM1555C1H100FA16D")
    >>> for part in results:
    ...     log.info(f"{part.jlcpcb_code}: {part.description}")

    # Get details for a specific C code
    >>> from supply_chain_monkey.jlc_scraper import get_jlcpcb_part_details
    >>> part = get_jlcpcb_part_details("C161145")
    >>> log.info(part.description)

    # Search without verification (faster, but no description)
    >>> results = search_jlcpcb_by_mpn("GCM1555C1H100FA16D", verify_parts=False)

    # Use in a right-click context menu
    >>> def on_right_click_search_jlc(selected_mpn):
    ...     results = search_jlcpcb_by_mpn(selected_mpn)
    ...     if len(results) == 1:
    ...         # Auto-fill single result
    ...         part = results[0]
    ...         update_field("JLCPCB Part #", part.jlcpcb_code)
    ...         update_field("Description", part.description)
    ...     elif len(results) > 1:
    ...         # Show selection dialog
    ...         show_selection_dialog(results)
"""

import logging
import re
from urllib.parse import quote_plus

import requests

log = logging.getLogger(__name__)


class JLCPartInfo:
    """Container for JLCPCB part information"""
    def __init__(self, jlcpcb_code: str, mpn: str = "", description: str = "", url: str = "", stock: int = 0, manufacturer: str = ""):
        self.jlcpcb_code = jlcpcb_code
        self.mpn = mpn
        self.description = description
        self.url = url
        self.stock = stock
        self.manufacturer = manufacturer

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'jlcpcb_code': self.jlcpcb_code,
            'mpn': self.mpn,
            'description': self.description,
            'url': self.url,
            'stock': self.stock,
            'manufacturer': self.manufacturer
        }

    def __repr__(self):
        return f"JLCPartInfo({self.jlcpcb_code}, {self.mpn}, stock={self.stock}, {self.description[:30]}...)"


def _normalize_mpn_token(value: str) -> str:
    return value.upper().replace("-", "").replace(" ", "")


def _fetch_jlcpcb_page(url: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def _scan_balanced(text: str, start_index: int, open_char: str, close_char: str) -> int:
    """
    Return the inclusive end index of a balanced region starting at start_index.
    """
    assert text[start_index] == open_char
    depth = 0
    in_string = False
    string_quote = ""
    escaped = False

    for index in range(start_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_quote:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            string_quote = char
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index

    raise ValueError(f"Unbalanced region starting at index {start_index}")


def _split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    brace_depth = 0
    bracket_depth = 0
    paren_depth = 0
    in_string = False
    string_quote = ""
    escaped = False

    for char in text:
        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_quote:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            string_quote = char
            current.append(char)
            continue

        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1

        if (
            char == delimiter
            and brace_depth == 0
            and bracket_depth == 0
            and paren_depth == 0
        ):
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
            continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)

    return parts


def _parse_js_object_pairs(object_text: str) -> dict[str, str]:
    if not (object_text.startswith("{") and object_text.endswith("}")):
        return {}

    inner = object_text[1:-1].strip()
    if not inner:
        return {}

    result: dict[str, str] = {}
    for item in _split_top_level(inner):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        result[key.strip().strip('"').strip("'")] = value.strip()
    return result


def _decode_js_string(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        content = raw[1:-1]
    else:
        content = raw
    content = content.replace("\\/", "/")
    return _decode_unicode_escapes(content)


def _parse_simple_js_value(raw: str):
    raw = raw.strip()
    if not raw:
        return ""
    if raw in {"null", "undefined"}:
        return ""
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.startswith(("\"", "'")) and raw.endswith(("\"", "'")):
        return _decode_js_string(raw)
    if re.fullmatch(r"-?\d+", raw):
        try:
            return int(raw)
        except ValueError:
            return raw
    if re.fullmatch(r"-?\d+\.\d+", raw):
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def _extract_nuxt_alias_map(html_text: str) -> dict[str, object]:
    prefix = "window.__NUXT__=(function("
    start = html_text.find(prefix)
    if start == -1:
        return {}

    params_start = start + len(prefix)
    params_end = html_text.find("){", params_start)
    if params_end == -1:
        return {}

    params = [p.strip() for p in html_text[params_start:params_end].split(",") if p.strip()]

    body_start = params_end + 1  # points at "{"
    try:
        body_end = _scan_balanced(html_text, body_start, "{", "}")
    except ValueError:
        return {}

    invoke_start = html_text.find("(", body_end + 1)
    if invoke_start == -1:
        return {}

    try:
        invoke_end = _scan_balanced(html_text, invoke_start, "(", ")")
    except ValueError:
        return {}

    args_text = html_text[invoke_start + 1:invoke_end]
    args = _split_top_level(args_text)

    alias_map: dict[str, object] = {}
    for index, name in enumerate(params):
        if index >= len(args):
            break
        alias_map[name] = _parse_simple_js_value(args[index])

    return alias_map


def _resolve_js_token(raw: str, alias_map: dict[str, object]):
    value = _parse_simple_js_value(raw)
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value):
        resolved = alias_map.get(value, value)
        if isinstance(resolved, str) and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", resolved) and resolved != value:
            return _resolve_js_token(resolved, alias_map)
        return resolved
    return value


def _extract_nuxt_table_objects(html_text: str) -> list[dict[str, str]]:
    objects: list[dict[str, str]] = []
    search_from = 0

    while True:
        marker = html_text.find("tableList:[", search_from)
        if marker == -1:
            break

        array_start = html_text.find("[", marker)
        if array_start == -1:
            break

        try:
            array_end = _scan_balanced(html_text, array_start, "[", "]")
        except ValueError:
            break

        array_text = html_text[array_start + 1:array_end]
        for item in _split_top_level(array_text):
            item = item.strip()
            if item.startswith("{") and item.endswith("}"):
                parsed = _parse_js_object_pairs(item)
                if parsed:
                    objects.append(parsed)

        search_from = array_end + 1

    return objects


def _extract_structured_search_results(html_text: str, expected_mpn: str = "") -> list[JLCPartInfo]:
    alias_map = _extract_nuxt_alias_map(html_text)
    rows = _extract_nuxt_table_objects(html_text)
    results: list[JLCPartInfo] = []
    seen_codes: set[str] = set()
    expected_normalized = _normalize_mpn_token(expected_mpn) if expected_mpn else ""

    for row in rows:
        code = str(_resolve_js_token(row.get("componentCode", ""), alias_map) or "").strip()
        if not re.fullmatch(r"C\d{4,9}", code):
            continue
        if code in seen_codes:
            continue

        mpn = str(_resolve_js_token(row.get("componentModelEn", ""), alias_map) or "").strip()
        if expected_normalized and mpn and _normalize_mpn_token(mpn) != expected_normalized:
            continue

        manufacturer = str(_resolve_js_token(row.get("componentBrandEn", ""), alias_map) or "").strip()
        description = str(_resolve_js_token(row.get("describe", ""), alias_map) or "").strip()
        url_suffix = str(_resolve_js_token(row.get("urlSuffix", ""), alias_map) or "").strip()
        stock_value = _resolve_js_token(row.get("stockCount", "0"), alias_map)
        try:
            stock = int(stock_value)
        except (TypeError, ValueError):
            stock = 0

        if url_suffix:
            part_url = f"https://jlcpcb.com/partdetail/{url_suffix}"
        else:
            part_url = f"https://jlcpcb.com/partdetail/{code}"

        results.append(JLCPartInfo(
            jlcpcb_code=code,
            mpn=mpn or expected_mpn,
            description=description,
            url=part_url,
            stock=stock,
            manufacturer=manufacturer,
        ))
        seen_codes.add(code)

    return results


def search_jlcpcb_by_mpn(mpn: str, verify_parts: bool = True, **kwargs) -> list[JLCPartInfo]:
    """
    Search JLCPCB for parts matching a manufacturer part number.

    Args:
        mpn: Manufacturer Part Number to search for
        verify_parts: If True, verify each C code by fetching detail page
        max_results: Maximum number of results to return (default unlimited)

    Returns:
        List of JLCPartInfo objects for matching parts
    """
    max_results = kwargs.get("max_results", 0)
    search_url = f"https://jlcpcb.com/parts/componentSearch?searchTxt={quote_plus(mpn)}"

    try:
        log.info(f"[JLCPCB] Searching for MPN: {mpn}")

        html_text = _fetch_jlcpcb_page(search_url)

        structured_results = _extract_structured_search_results(html_text, expected_mpn=mpn)
        if structured_results:
            log.info(f"[JLCPCB] Found {len(structured_results)} structured result(s) in Nuxt data")
        else:
            log.info("[JLCPCB] No structured Nuxt results found; falling back to page-wide extraction")

        # Extract C codes from HTML (C codes can be 4-9 digits)
        c_code_pattern = r'C\d{4,9}'
        all_c_codes = re.findall(c_code_pattern, html_text)
        unique_c_codes = list(set(all_c_codes))

        log.info(f"[JLCPCB] Found {len(unique_c_codes)} potential C codes in fallback search results")

        results = []

        if structured_results:
            # Nuxt extraction succeeded — use these directly, no verification needed
            results.extend(structured_results)
        elif verify_parts:
            # No structured data — verify C-codes via LCSC API (fast) then
            # fall back to JLCPCB scraper for codes LCSC doesn't have
            limit = max_results if max_results > 0 else len(unique_c_codes)
            log.info(f"[JLCPCB] Verifying up to {limit} of {len(unique_c_codes)} C codes via LCSC API...")
            verified = 0
            for i, c_code in enumerate(unique_c_codes, 1):
                if verified >= limit:
                    log.info(f"[JLCPCB] Reached max_results ({limit}), stopping verification")
                    break
                try:
                    from .lcsc_api import get_lcsc_detail
                    lcsc_result = get_lcsc_detail(c_code)
                    if lcsc_result and lcsc_result.product_model:
                        # Check MPN match
                        lcsc_mpn = lcsc_result.product_model.upper().replace("-", "").replace(" ", "")
                        expected = mpn.upper().replace("-", "").replace(" ", "")
                        if expected in lcsc_mpn or lcsc_mpn in expected:
                            log.info(f"[JLCPCB] LCSC verified: {c_code} - {lcsc_result.product_model}")
                            results.append(JLCPartInfo(
                                jlcpcb_code=c_code,
                                mpn=lcsc_result.product_model,
                                description=lcsc_result.description,
                                url=f"https://jlcpcb.com/partdetail/{c_code}",
                                stock=lcsc_result.stock if isinstance(lcsc_result.stock, int) else 0,
                                manufacturer=lcsc_result.brand,
                            ))
                            verified += 1
                            continue
                except Exception as exc:
                    log.debug(f"[JLCPCB] LCSC lookup failed for {c_code}: {exc}")

                # Fall back to JLCPCB scraper for this code
                log.info(f"[JLCPCB] Scraper fallback for {c_code} ({i}/{len(unique_c_codes)})...")
                part_info = get_jlcpcb_part_details(c_code, expected_mpn=mpn)
                if part_info:
                    log.info(f"[JLCPCB] Validated: {c_code} - {part_info.mpn}")
                    results.append(part_info)
                    verified += 1
                else:
                    log.info(f"[JLCPCB] Rejected: {c_code} (MPN mismatch or error)")
        else:
            # Return unverified results
            for c_code in unique_c_codes:
                results.append(JLCPartInfo(
                    jlcpcb_code=c_code,
                    mpn=mpn,
                    url=f"https://jlcpcb.com/partdetail/{c_code}"
                ))

        # If page-based methods found nothing, try Claude as fallback
        if not results:
            log.info("[JLCPCB] No valid parts found with regex, trying Claude AI fallback...")
            try:
                from .claude_scraper_helper import find_c_code_with_claude

                c_code = find_c_code_with_claude(html_text, mpn, supplier="JLCPCB")
                if c_code:
                    log.info(f"[JLCPCB] Claude found C code: {c_code}")
                    part_info = get_jlcpcb_part_details(c_code, expected_mpn=mpn)
                    if part_info:
                        results.append(part_info)
                        log.info(f"[JLCPCB] Claude successfully found {c_code} for {mpn}")
                    else:
                        log.warning(f"[JLCPCB] Claude found {c_code} but validation failed")
                else:
                    log.info("[JLCPCB] Claude could not find matching C code")
            except ImportError:
                log.warning("[JLCPCB] Claude helper not available (missing anthropic package)")
            except Exception as e:
                log.error(f"[JLCPCB] Claude fallback error: {str(e)}")

        # Apply max_results cap to final results (including structured)
        if max_results > 0 and len(results) > max_results:
            results = results[:max_results]

        if results:
            log.info(f"[JLCPCB] Search complete: Found {len(results)} valid part(s)")
        else:
            log.warning(f"[JLCPCB] No parts found for {mpn}")

        return results

    except Exception as e:
        log.error(f"[JLCPCB] Error searching for {mpn}: {str(e)}")
        return []


def get_jlcpcb_part_details(c_code: str, expected_mpn: str = "") -> JLCPartInfo | None:
    """
    Get detailed information for a JLCPCB part by its C code.

    Args:
        c_code: JLCPCB part number (e.g., C668319)
        expected_mpn: Expected manufacturer part number (for validation)

    Returns:
        JLCPartInfo object if successful, None otherwise
    """
    detail_url = f"https://jlcpcb.com/partdetail/{c_code}"

    try:
        html_text = _fetch_jlcpcb_page(detail_url)

        # Extract MPN from the detail page
        found_mpn = _extract_mpn(html_text, expected_mpn)

        # If we have an expected MPN and the found MPN doesn't match, reject this part
        if expected_mpn and found_mpn:
            # Normalize for comparison (case-insensitive, remove whitespace/hyphens)
            expected_normalized = expected_mpn.upper().replace("-", "").replace(" ", "")
            found_normalized = found_mpn.upper().replace("-", "").replace(" ", "")

            if expected_normalized != found_normalized:
                # This C code is for a different part - reject it
                return None

        # Extract description
        description = _extract_description(html_text)

        # Extract stock
        stock = _extract_stock(html_text)

        # Extract manufacturer
        manufacturer = _extract_manufacturer(html_text)

        return JLCPartInfo(
            jlcpcb_code=c_code,
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
    Extract manufacturer name from JLCPCB detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Extracted manufacturer name or empty string
    """
    # Try title tag first: "NRF52840-QIAA-R | Nordic Semicon | RF Transceiver ICs | JLCPCB"
    title_match = re.search(r'<title>([^<]+)</title>', html_text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1)
        parts = [p.strip() for p in title.split('|')]
        # Manufacturer is typically the second part
        if len(parts) >= 2 and parts[1] and parts[1].upper() != 'JLCPCB':
            return parts[1]

    # Try JavaScript object patterns
    manufacturer_patterns = [
        r'"brand":\s*"([^"]+)"',
        r'"manufacturer":\s*"([^"]+)"',
        r'brand:\s*"([^"]+)"',
        r'manufacturer:\s*"([^"]+)"',
    ]

    for pattern in manufacturer_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            manufacturer = match.group(1)
            # Skip generic or placeholder values
            if manufacturer and manufacturer.upper() not in ['MANUFACTURER', 'BRAND', 'N/A', 'UNKNOWN']:
                return manufacturer

    return ""


def _extract_mpn(html_text: str, expected_mpn: str = "") -> str | None:
    """
    Extract manufacturer part number from JLCPCB detail page HTML.

    Args:
        html_text: HTML content from detail page
        expected_mpn: Expected MPN to look for

    Returns:
        Extracted MPN or None
    """
    mpn_patterns = [
        rf'{re.escape(expected_mpn)}' if expected_mpn else None,  # Exact match
        r'MFR\.Part.*?([A-Z0-9\-]+)',  # MFR.Part field
        r'Mfr\.Part.*?([A-Z0-9\-]+)',  # Mfr.Part field
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
    Extract part description from JLCPCB detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Extracted description or empty string
    """
    desc_patterns = [
        r'describe\s*:\s*"([^"]+)"',  # window.__NUXT__ object (primary source, unquoted key)
        r'"describe"\s*:\s*"([^"]+)"',  # window.__NUXT__ object (quoted key)
        r'<h1[^>]*>([^<]+)</h1>',  # Main title
        r'"description"\s*:\s*"([^"]+)"',  # JSON metadata
        r'Description.*?<td[^>]*>([^<]+)</td>',  # Table row
    ]

    for pattern in desc_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            description = match.group(1).strip()

            # Decode unicode escape sequences (e.g., \u002F -> /)
            description = _decode_unicode_escapes(description)

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
    Extract stock quantity from JLCPCB detail page HTML.

    Args:
        html_text: HTML content from detail page

    Returns:
        Stock quantity as integer, or 0 if not found
    """
    stock_patterns = [
        r'stock\s*:\s*(\d+)',  # window.__NUXT__ object (primary source, unquoted key)
        r'"stock"\s*:\s*(\d+)',  # window.__NUXT__ object (quoted key)
        r'Stock\s*[:\s]+(\d+)',  # Stock label
        r'Inventory\s*[:\s]+(\d+)',  # Inventory label
        r'>(\d+)\s*In\s*Stock<',  # "X In Stock" text
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
def verify_jlc_code(c_code: str, expected_mpn: str = "") -> dict | None:
    """
    Legacy function for backwards compatibility.

    Returns dictionary format instead of JLCPartInfo object.
    """
    part_info = get_jlcpcb_part_details(c_code, expected_mpn)
    return part_info.to_dict() if part_info else None


def scrape_jlcpcb_search(mpn: str) -> list[dict]:
    """
    Legacy function for backwards compatibility.

    Returns list of dictionaries instead of JLCPartInfo objects.
    """
    results = search_jlcpcb_by_mpn(mpn, verify_parts=True)
    return [part.to_dict() for part in results]


if __name__ == "__main__":
    # Example usage and testing
    log.info("=== JLCPCB Scraper Test ===\n")

    # Test 1: Search by MPN
    mpn = "GCM1555C1H100FA16D"
    log.info(f"Searching for MPN: {mpn}")
    results = search_jlcpcb_by_mpn(mpn)
    log.info(f"Found {len(results)} results:")
    for part in results:
        log.info(f"  {part.jlcpcb_code}: {part.description}")
    log.info()

    # Test 2: Get specific part details
    c_code = "C161145"
    log.info(f"Getting details for C code: {c_code}")
    part = get_jlcpcb_part_details(c_code)
    if part:
        log.info(f"  MPN: {part.mpn}")
        log.info(f"  Description: {part.description}")
        log.info(f"  URL: {part.url}")
    else:
        log.info("  No details found")
