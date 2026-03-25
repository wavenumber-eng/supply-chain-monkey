"""
Claude-based HTML scraper for JLCPCB/LCSC part information.

Uses Claude API to intelligently parse HTML and extract part data,
which is more robust than regex patterns.

Usage:
    >>> from supply_chain_monkey.claude_scraper_helper import extract_part_info_with_claude
    >>> html = "<html>...</html>"
    >>> part_info = extract_part_info_with_claude(html, expected_mpn="STM32F407")
    >>> if part_info:
    ...     log.info(f"MPN: {part_info['mpn']}")
    ...     log.info(f"Description: {part_info['description']}")
"""

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

from .env import ensure_env_loaded

ensure_env_loaded()


def extract_part_info_with_claude(
    html_content: str,
    expected_mpn: str = "",
    supplier: str = "JLCPCB"
) -> dict[str, Any] | None:
    """
    Use Claude to extract part information from HTML.

    Tries progressively more powerful models if extraction fails:
    1. claude-3-5-haiku (fast, cheap)
    2. claude-3-5-sonnet (balanced, more capable)
    3. claude-opus (most powerful, expensive)

    Args:
        html_content: HTML content from part detail page
        expected_mpn: Expected manufacturer part number (for validation)
        supplier: Supplier name (JLCPCB or LCSC)

    Returns:
        Dict with keys: mpn, description, stock, manufacturer
        Returns None if extraction failed or MPN doesn't match
    """
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        log.info("Warning: ANTHROPIC_API_KEY not found or not configured in .env")
        return None

    try:
        import anthropic
    except ImportError:
        log.info("Warning: anthropic package not installed; install the optional 'ai' extra to enable Claude helpers")
        return None

    # Model cascade: try cheaper models first, escalate if needed
    # Using latest available models as of January 2025
    models = [
        ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 (fast & cheap)"),
        ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5 (latest & best)")
    ]

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Truncate HTML if too long (Claude has token limits)
        max_html_length = 100000  # characters
        if len(html_content) > max_html_length:
            html_content = html_content[:max_html_length]

        # Build prompt
        prompt = f"""I need you to extract part information from this {supplier} product detail page HTML.

Please find and extract the following information:
1. Manufacturer Part Number (MPN) - The actual manufacturer's part number
2. Manufacturer Name - The company that makes this part
3. Description - The part description
4. Stock quantity - How many are in stock (as a number)

Expected MPN: {expected_mpn if expected_mpn else "unknown"}

IMPORTANT VALIDATION:
- If you find an MPN, verify it matches the expected MPN: "{expected_mpn}"
- Normalize both for comparison (uppercase, remove hyphens/spaces)
- If they don't match, return "validation_failed": true

Return ONLY valid JSON in this exact format:
{{
    "mpn": "actual MPN found",
    "manufacturer": "manufacturer name",
    "description": "part description",
    "stock": 12345,
    "validation_failed": false
}}

If you cannot find the information, return:
{{
    "validation_failed": true,
    "reason": "explanation"
}}

HTML content:
{html_content}
"""

        # Try each model in sequence
        # Only escalate if no MPN found (not just validation failures)
        last_error = None

        for model_id, model_name in models:
            try:
                log.info(f"Trying {model_name}...")

                # Call Claude API
                message = client.messages.create(
                    model=model_id,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                # Parse response
                response_text = message.content[0].text.strip()

                # Try to parse the result
                result, found_mpn = _parse_claude_response(response_text, expected_mpn, return_mpn_status=True)

                if result:
                    log.info(f"✓ {model_name} successfully extracted and validated part info")
                    return result
                elif found_mpn:
                    # Found an MPN but it didn't match expected - stop here, don't waste money
                    log.info(f"✗ {model_name} found MPN but validation failed (wrong part). Not escalating.")
                    return None
                else:
                    # Couldn't find MPN at all - try next model
                    log.info(f"✗ {model_name} could not find MPN, trying next model...")
                    continue

            except Exception as e:
                last_error = e
                log.info(f"✗ {model_name} error: {str(e)}")
                continue

        # All models failed
        log.info(f"All models failed to find MPN. Last error: {last_error}")
        return None

    except Exception as e:
        log.info(f"Error using Claude for scraping: {str(e)}")
        return None


def _parse_claude_response(response_text: str, expected_mpn: str = "", return_mpn_status: bool = False):
    """
    Parse Claude's response and validate the extracted data.

    Args:
        response_text: Raw text response from Claude
        expected_mpn: Expected MPN for validation
        return_mpn_status: If True, returns (result, mpn_found) tuple

    Returns:
        If return_mpn_status=False: Dict with part info or None if validation failed
        If return_mpn_status=True: Tuple of (result_dict or None, mpn_was_found bool)
    """
    import json
    import re

    try:
        # Look for JSON object in response
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if not json_match:
            return (None, False) if return_mpn_status else None

        result = json.loads(json_match.group(0))

        # Check validation
        if result.get("validation_failed"):
            # Claude couldn't find the data
            return (None, False) if return_mpn_status else None

        # Check if MPN was found
        found_mpn = result.get("mpn")
        if not found_mpn:
            return (None, False) if return_mpn_status else None

        # MPN was found - now validate it matches expected
        if expected_mpn:
            found_mpn_norm = found_mpn.upper().replace("-", "").replace(" ", "")
            expected_norm = expected_mpn.upper().replace("-", "").replace(" ", "")

            if found_mpn_norm != expected_norm:
                # MPN doesn't match - check if description is very similar (might be variant)
                # If we have both MPNs in the description, they might be cross-references
                description = result.get("description", "").upper()

                # Check if both MPNs appear in description (cross-reference case)
                if expected_norm in description and found_mpn_norm in description:
                    log.info(f"  Note: Found cross-reference - description contains both '{expected_mpn}' and '{found_mpn}'")
                    # Still accept it - might be equivalent part or cross-reference
                    return (result, True) if return_mpn_status else result

                # Check if expected MPN is in the description but found MPN is not
                # (Might have extracted wrong field as MPN)
                if expected_norm in description and found_mpn_norm not in description:
                    log.info("  Note: Expected MPN found in description, overriding extracted MPN")
                    result["mpn"] = expected_mpn  # Override with expected
                    return (result, True) if return_mpn_status else result

                # MPNs truly don't match and no cross-reference - wrong part
                log.info(f"  MPN mismatch: found '{found_mpn}' vs expected '{expected_mpn}'")
                return (None, True) if return_mpn_status else None

        # Success - MPN found and validated
        return (result, True) if return_mpn_status else result

    except Exception:
        return (None, False) if return_mpn_status else None


def find_c_code_with_claude(
    search_page_html: str,
    expected_mpn: str,
    supplier: str = "JLCPCB"
) -> str | None:
    """
    Use Claude to find the correct C code from a search results page.

    This is more efficient than scraping individual detail pages - Claude can
    analyze the search results and identify the correct C code for the MPN.

    Args:
        search_page_html: HTML from JLCPCB/LCSC search results page
        expected_mpn: The manufacturer part number we're searching for
        supplier: Supplier name (JLCPCB or LCSC)

    Returns:
        C code (e.g., "C2040") if found and validated, None otherwise
    """
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return None

    try:
        try:
            import anthropic
        except ImportError:
            log.info("Warning: anthropic package not installed; install the optional 'ai' extra to enable Claude helpers")
            return None

        client = anthropic.Anthropic(api_key=api_key)

        # Truncate HTML if too long
        max_html_length = 100000
        if len(search_page_html) > max_html_length:
            search_page_html = search_page_html[:max_html_length]

        prompt = f"""I need you to find the correct {supplier} C code for a specific part from this search results page.

Target MPN: {expected_mpn}

Please analyze the search results and find:
1. The C code (like C2040, C25239040, etc.) that corresponds to this exact MPN
2. Make sure the MPN matches (normalize for comparison - uppercase, ignore hyphens/spaces)
3. If there are multiple C codes for the same MPN (different packaging), return the first one

Return ONLY valid JSON:
{{
    "c_code": "C2040",
    "mpn_found": "TPS543620RPYR",
    "confidence": "high",
    "found": true
}}

If you cannot find a matching C code:
{{
    "found": false,
    "reason": "explanation"
}}

HTML content:
{search_page_html}
"""

        # Try Haiku first (cheap and fast for this simple task)
        log.info(f"Using Claude to find C code for {expected_mpn}...")

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Parse response
        import json
        import re

        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if not json_match:
            return None

        result = json.loads(json_match.group(0))

        if not result.get("found"):
            log.info(f"  Claude couldn't find C code: {result.get('reason', 'unknown')}")
            return None

        c_code = result.get("c_code")
        found_mpn = result.get("mpn_found", "")

        # Validate the MPN matches
        if found_mpn:
            found_norm = found_mpn.upper().replace("-", "").replace(" ", "")
            expected_norm = expected_mpn.upper().replace("-", "").replace(" ", "")

            if found_norm != expected_norm:
                log.info(f"  MPN mismatch: Claude found '{found_mpn}' but expected '{expected_mpn}'")
                return None

        log.info(f"  Found C code: {c_code} (confidence: {result.get('confidence', 'unknown')})")
        return c_code

    except Exception as e:
        log.info(f"Error using Claude to find C code: {str(e)}")
        return None


def test_claude_scraper():
    """Test the Claude-based scraper"""
    import requests

    # Test with a real JLCPCB part
    c_code = "C2040"
    expected_mpn = "TPS543620RPYR"

    log.info(f"Testing Claude scraper with C{c_code}")
    log.info(f"Expected MPN: {expected_mpn}")
    log.info("=" * 70)

    # Fetch HTML
    url = f"https://jlcpcb.com/partdetail/{c_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        log.info(f"Fetched HTML ({len(response.text)} chars)")

        # Use Claude to extract
        result = extract_part_info_with_claude(
            response.text,
            expected_mpn=expected_mpn,
            supplier="JLCPCB"
        )

        if result:
            log.info("\nExtracted information:")
            log.info(f"  MPN: {result.get('mpn')}")
            log.info(f"  Manufacturer: {result.get('manufacturer')}")
            log.info(f"  Description: {result.get('description')}")
            log.info(f"  Stock: {result.get('stock')}")
        else:
            log.info("\nFailed to extract information")
    else:
        log.info(f"Failed to fetch page: HTTP {response.status_code}")


if __name__ == "__main__":
    test_claude_scraper()
