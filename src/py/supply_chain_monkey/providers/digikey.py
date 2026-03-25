"""
Digikey Supplier Implementation

This module implements the SupplierInterface for Digikey using their official
Product Information API v4.

Digikey is a major electronics distributor with a comprehensive parts database.
Their API requires OAuth2 authentication and provides detailed part information
including stock, pricing, lifecycle status, and datasheets.

Features:
    - OAuth2 authentication (two-legged client credentials flow)
    - Search by manufacturer part number
    - Get details by Digikey part number
    - Stock availability and pricing information
    - Lifecycle status (Active, Obsolete, EOL, etc.)
    - Rate limit handling with exponential backoff

Usage:
    >>> from supply_chain_monkey import create_supplier, SupplierType
    >>>
    >>> # Create with credentials from .env
    >>> digikey = create_supplier(SupplierType.DIGIKEY)
    >>>
    >>> # Or provide credentials explicitly
    >>> digikey = create_supplier(
    ...     SupplierType.DIGIKEY,
    ...     client_id="your_id",
    ...     client_secret="your_secret"
    ... )
    >>>
    >>> # Search by MPN
    >>> results = digikey.search_by_mpn("STM32F407VGT6")
    >>> for part in results:
    ...     log.info(f"{part.supplier_part_number}: {part.stock_quantity} in stock")
    >>>
    >>> # Get specific Digikey part number details
    >>> part = digikey.get_part_details("296-STM32F407VGT6-ND")
"""

import logging
import os
import time

import requests

log = logging.getLogger(__name__)


from .base import SupplierInterface, SupplierPartInfo, SupplierType, resolve_stock


class DigikeySupplier(SupplierInterface):
    """
    Digikey implementation of the supplier interface.

    Uses Digikey's Product Information API v4 with OAuth2 authentication.

    Authentication:
        Uses two-legged OAuth (client credentials flow) - no browser interaction needed.
        Access tokens are cached and automatically refreshed when expired.

    Rate Limiting:
        Digikey enforces strict rate limits. This implementation handles 429 responses
        with exponential backoff and respects Retry-After headers.

    API Documentation:
        https://developer.digikey.com/products/product-information-v4
    """

    # API endpoints
    BASE_URL = "https://api.digikey.com"
    TOKEN_URL = f"{BASE_URL}/v1/oauth2/token"
    SEARCH_URL = f"{BASE_URL}/products/v4/search/keyword"
    DETAILS_URL = f"{BASE_URL}/products/v4/search"
    SUBSTITUTIONS_URL = f"{BASE_URL}/products/v4/search"  # /{productNumber}/substitutions

    # Default locale settings
    DEFAULT_LOCALE_SITE = "US"
    DEFAULT_LOCALE_LANGUAGE = "en"
    DEFAULT_LOCALE_CURRENCY = "USD"

    def __init__(self, **credentials):
        """
        Initialize Digikey supplier client.

        Args:
            **credentials: Authentication credentials
                client_id: Digikey Client ID (required)
                client_secret: Digikey Client Secret (required)
                locale_site: Site locale (default: "US")
                locale_language: Language (default: "en")
                locale_currency: Currency (default: "USD")

        If credentials are not provided, will attempt to load from environment:
            - DIGIKEY_CLIENT_ID
            - DIGIKEY_CLIENT_SECRET
        """
        super().__init__(**credentials)

        # Get credentials from params or environment
        self.client_id = credentials.get('client_id') or os.getenv('DIGIKEY_CLIENT_ID')
        self.client_secret = credentials.get('client_secret') or os.getenv('DIGIKEY_CLIENT_SECRET')

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Digikey credentials required! Provide client_id/client_secret or set "
                "DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET environment variables."
            )

        # Locale settings
        self.locale_site = credentials.get('locale_site', self.DEFAULT_LOCALE_SITE)
        self.locale_language = credentials.get('locale_language', self.DEFAULT_LOCALE_LANGUAGE)
        self.locale_currency = credentials.get('locale_currency', self.DEFAULT_LOCALE_CURRENCY)

        # Token management
        self._access_token = None
        self._token_expires_at = 0

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.2  # Minimum 200ms between requests

    @property
    def supplier_type(self) -> SupplierType:
        """Return Digikey supplier type."""
        return SupplierType.DIGIKEY

    @property
    def parameter_field_name(self) -> str:
        """
        Return the Part parameter field name for Digikey.

        Returns:
            "Digikey Part #"
        """
        return "Digikey Part #"

    def _get_access_token(self) -> str:
        """
        Get a valid OAuth2 access token.

        Caches the token and only requests a new one when expired.

        Returns:
            Valid access token

        Raises:
            Exception if token request fails
        """
        # Return cached token if still valid (with 60 second buffer)
        if self._access_token and time.time() < (self._token_expires_at - 60):
            return self._access_token

        # Request new token
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data, headers=headers, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 600)  # Default 10 minutes
            self._token_expires_at = time.time() + expires_in

            return self._access_token

        except Exception as e:
            raise Exception(f"Failed to get Digikey access token: {str(e)}")

    def _make_request(self, url: str, method: str = "GET", json_data: dict = None,
                      max_retries: int = 3) -> dict | None:
        """
        Make an authenticated API request with rate limiting and retry logic.

        Args:
            url: API endpoint URL
            method: HTTP method ("GET" or "POST")
            json_data: JSON request body (for POST)
            max_retries: Maximum number of retries for rate limits

        Returns:
            Response JSON data or None on failure
        """
        # Rate limiting - enforce minimum interval between requests
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)

        # Get fresh access token
        access_token = self._get_access_token()

        # Build headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-DIGIKEY-Client-Id': self.client_id,
            'Content-Type': 'application/json',
            'X-DIGIKEY-Locale-Site': self.locale_site,
            'X-DIGIKEY-Locale-Language': self.locale_language,
            'X-DIGIKEY-Locale-Currency': self.locale_currency
        }

        # Retry loop with exponential backoff
        wait_time = 1
        for attempt in range(max_retries):
            try:
                self._last_request_time = time.time()

                if method == "POST":
                    response = requests.post(url, headers=headers, json=json_data, timeout=15)
                else:
                    response = requests.get(url, headers=headers, timeout=15)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    # Check for Retry-After header
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = wait_time * 2  # Exponential backoff

                    log.info(f"Digikey rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                # Raise for other error status codes
                response.raise_for_status()

                return response.json()

            except requests.exceptions.RequestException as e:
                log.info(f"Digikey API request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2

        return None

    def search_by_mpn(self, manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
        """
        Search Digikey for parts matching a manufacturer part number.

        Args:
            manufacturer_part_number: MPN to search for
            **kwargs: Optional parameters
                limit: int = 50 (max results to return, 1-50)
                offset: int = 0 (pagination offset)
                exact_only: bool = False (return only exact matches)

        Returns:
            List of SupplierPartInfo objects (empty list on error)
        """
        try:
            # Extract options
            limit = min(kwargs.get('limit', 50), 50)  # API max is 50
            offset = kwargs.get('offset', 0)
            exact_only = kwargs.get('exact_only', False)

            # Build request body
            body = {
                'Keywords': manufacturer_part_number,
                'Limit': limit,
                'Offset': offset
            }

            # Make API request
            data = self._make_request(self.SEARCH_URL, method="POST", json_data=body)

            if not data:
                return []

            # Parse results
            results = []

            # Check exact matches first
            exact_matches = data.get('ExactMatches', [])
            if exact_matches:
                for product in exact_matches:
                    # Get all packaging variations for this product
                    variant_infos = self._parse_product_variations(product, manufacturer_part_number)
                    results.extend(variant_infos)

            # Add regular matches if not exact_only
            if not exact_only:
                products = data.get('Products', [])
                for product in products:
                    # Skip if already in exact matches
                    mpn = product.get('ManufacturerProductNumber', '')
                    if mpn and mpn in [r.manufacturer_part_number for r in results]:
                        continue

                    # Get all packaging variations for this product
                    variant_infos = self._parse_product_variations(product, manufacturer_part_number)
                    results.extend(variant_infos)

            return results

        except Exception as e:
            log.info(f"Error searching Digikey for {manufacturer_part_number}: {str(e)}")
            return []

    def get_part_details(self, supplier_part_number: str, **kwargs) -> SupplierPartInfo | None:
        """
        Get detailed information for a specific Digikey part number.

        Args:
            supplier_part_number: Digikey part number (e.g., "296-STM32F407VGT6-ND")
            **kwargs: Optional parameters
                expected_mpn: str (expected MPN for validation)

        Returns:
            SupplierPartInfo object or None if not found
        """
        try:
            # Build URL
            url = f"{self.DETAILS_URL}/{supplier_part_number}/productdetails"

            # Make API request
            data = self._make_request(url, method="GET")

            if not data:
                return None

            # Parse product
            expected_mpn = kwargs.get('expected_mpn', '')
            return self._parse_product(data, expected_mpn)

        except Exception as e:
            log.info(f"Error getting Digikey details for {supplier_part_number}: {str(e)}")
            return None

    def _parse_product_variations(self, product: dict, search_mpn: str = "") -> list[SupplierPartInfo]:
        """
        Parse all packaging variations from a Digikey product.

        Args:
            product: Product dict from API response
            search_mpn: Original search MPN

        Returns:
            List of SupplierPartInfo objects (one per packaging variant)
        """
        variations_list = []

        # Check if ProductVariations exists
        variations = product.get('ProductVariations', [])

        if variations:
            # Multiple packaging options available - create one entry per variant
            for variation in variations:
                # Create a copy of the product with this specific variation
                product_copy = product.copy()
                product_copy['DigiKeyProductNumber'] = variation.get('DigiKeyProductNumber', '')
                product_copy['PackageType'] = variation.get('PackageType', {})

                # Parse this variation
                part_info = self._parse_product(product_copy, search_mpn)
                if part_info:
                    variations_list.append(part_info)
        else:
            # No variations - parse the product as-is
            part_info = self._parse_product(product, search_mpn)
            if part_info:
                variations_list.append(part_info)

        return variations_list

    def _parse_product(self, product: dict, search_mpn: str = "") -> SupplierPartInfo | None:
        """
        Parse a Digikey product object into SupplierPartInfo.

        Args:
            product: Product dict from API response
            search_mpn: Original search MPN (for fallback)

        Returns:
            SupplierPartInfo object or None if parsing fails
        """
        try:
            # Extract manufacturer info
            manufacturer_obj = product.get('Manufacturer', {})
            manufacturer = manufacturer_obj.get('Name', '') if isinstance(manufacturer_obj, dict) else ''

            # Extract MPN
            mpn = product.get('ManufacturerProductNumber', search_mpn)

            # Extract Digikey part number
            # In search results, it's in ProductVariations[0].DigiKeyProductNumber
            # In product details, it might be at top level
            digikey_pn = (
                product.get('DigiKeyProductNumber') or
                product.get('DigiKeyPartNumber') or
                product.get('ProductNumber') or
                ""
            )

            # If not found at top level, check ProductVariations
            if not digikey_pn:
                variations = product.get('ProductVariations', [])
                if variations and len(variations) > 0:
                    digikey_pn = variations[0].get('DigiKeyProductNumber', '')

            # Extract description
            description_obj = product.get('Description', {})
            if isinstance(description_obj, dict):
                description = description_obj.get('ProductDescription', '')
            else:
                description = str(description_obj) if description_obj else ''

            # Extract URLs
            product_url = product.get('ProductUrl', '')
            datasheet_url = product.get('DatasheetUrl', '')

            # Extract lifecycle status
            lifecycle = ""
            if product.get('Discontinued'):
                lifecycle = "Discontinued"
            elif product.get('EndOfLife'):
                lifecycle = "End of Life"
            elif product.get('NormallyStocking'):
                lifecycle = "Active"
            else:
                product_status = product.get('ProductStatus', {})
                if isinstance(product_status, dict):
                    lifecycle = product_status.get('Status', '')

            # Extract stock with status
            stock_qty, stock_status = resolve_stock(
                product.get('QuantityAvailable'), lifecycle
            )

            # Extract pricing
            price_breaks = []
            unit_price = product.get('UnitPrice')
            if unit_price:
                try:
                    price_breaks.append({
                        "qty": 1,
                        "unit_price": float(unit_price),
                        "currency": "USD",
                    })
                except (TypeError, ValueError):
                    pass

            # Build SupplierPartInfo
            return SupplierPartInfo(
                supplier=SupplierType.DIGIKEY,
                supplier_part_number=digikey_pn,
                manufacturer=manufacturer,
                manufacturer_part_number=mpn,
                description=description,
                datasheet_url=datasheet_url,
                product_url=product_url,
                stock_quantity=stock_qty,
                stock_status=stock_status,
                price_breaks=price_breaks,
                lifecycle_status=lifecycle,
                extra_data=product,
            )

        except Exception as e:
            log.info(f"Error parsing Digikey product: {str(e)}")
            return None

    def validate_credentials(self) -> bool:
        """
        Validate Digikey credentials by attempting to get an access token.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            self._get_access_token()
            return True
        except Exception:
            return False


# Convenience function for quick searches
def search_digikey(manufacturer_part_number: str, **kwargs) -> list[SupplierPartInfo]:
    """
    Convenience function for quick Digikey searches.

    Args:
        manufacturer_part_number: MPN to search for
        **kwargs: Additional search options (passed to search_by_mpn)

    Returns:
        List of SupplierPartInfo objects

    Example:
        >>> from supply_chain_monkey.digikey_supplier import search_digikey
        >>> results = search_digikey("STM32F407VGT6")
        >>> for part in results:
        ...     log.info(part.supplier_part_number)
    """
    digikey = DigikeySupplier()
    return digikey.search_by_mpn(manufacturer_part_number, **kwargs)


if __name__ == "__main__":
    # Test the Digikey supplier implementation
    log.info("=== Digikey Supplier Test ===\n")

    # Load .env file if not already loaded
    def load_env():
        """Load .env file from project root"""
        env_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent.parent.parent / ".env"
        ]
        for env_path in env_paths:
            if env_path.exists():
                log.info(f"Loading .env from: {env_path}\n")
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"').strip("'")
                return True
        return False

    if not os.getenv('DIGIKEY_CLIENT_ID'):
        if not load_env():
            log.info("[ERROR] Could not find .env file!")
            exit(1)

    try:
        digikey = DigikeySupplier()

        # Test 1: Validate credentials
        log.info("1. Validating credentials...")
        if digikey.validate_credentials():
            log.info("   [OK] Credentials valid\n")
        else:
            log.info("   [ERROR] Invalid credentials\n")
            exit(1)

        # Test 2: Search by MPN
        test_mpn = "STM32F407VGT6"
        log.info(f"2. Searching for MPN: {test_mpn}")
        results = digikey.search_by_mpn(test_mpn)
        log.info(f"   Found {len(results)} results:")
        for i, part in enumerate(results[:5], 1):
            log.info(f"   {i}. {part.supplier_part_number}")
            log.info(f"      MPN: {part.manufacturer_part_number}")
            log.info(f"      Mfr: {part.manufacturer}")
            log.info(f"      Stock: {part.stock_quantity}")
            log.info(f"      Status: {part.lifecycle_status}")
        log.info()

        # Test 3: Verify parameter field name
        log.info(f"3. Parameter field name: {digikey.parameter_field_name}")
        log.info("   (Should stay stable for downstream consumers)")

    except Exception as e:
        log.info(f"[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
