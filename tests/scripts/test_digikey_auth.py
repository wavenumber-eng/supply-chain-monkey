"""
Test script for Digikey API authentication.

This script tests if your Digikey Client ID and Client Secret work
by attempting to get an OAuth2 access token and make a simple search.

Usage:
    python test_digikey_auth.py

Required .env entries:
    DIGIKEY_CLIENT_ID=your_client_id
    DIGIKEY_CLIENT_SECRET=your_client_secret
"""

import os

import requests
from supply_chain_monkey.env import ensure_env_loaded


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")


def load_credentials():
    """Load Digikey credentials from .env file"""
    env_vars = ensure_env_loaded()
    if env_vars:
        log_info("Loaded .env credentials from the local supply_chain_monkey env helper")

    client_id = os.getenv('DIGIKEY_CLIENT_ID')
    client_secret = os.getenv('DIGIKEY_CLIENT_SECRET')

    return client_id, client_secret


def get_access_token(client_id, client_secret):
    """
    Get OAuth2 access token using two-legged OAuth (client credentials flow).

    This is simpler than three-legged OAuth and doesn't require browser interaction.
    """
    log_info("Attempting to get OAuth2 access token...")

    # Digikey's token endpoint
    token_url = "https://api.digikey.com/v1/oauth2/token"

    # Prepare token request
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(token_url, data=data, headers=headers, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 'unknown')
            log_success(f"Got access token! (expires in {expires_in} seconds)")
            return access_token
        else:
            log_error(f"Token request failed: HTTP {response.status_code}")
            log_error(f"Response: {response.text}")
            return None

    except Exception as e:
        log_error(f"Exception during token request: {str(e)}")
        return None


def test_search(access_token, client_id):
    """
    Test searching for a part using the Digikey API.
    """
    log_info("Testing keyword search for 'STM32F407VGT6'...")

    # API endpoint
    search_url = "https://api.digikey.com/products/v4/search/keyword"

    # Request headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-DIGIKEY-Client-Id': client_id,
        'Content-Type': 'application/json',
        'X-DIGIKEY-Locale-Site': 'US',
        'X-DIGIKEY-Locale-Language': 'en',
        'X-DIGIKEY-Locale-Currency': 'USD'
    }

    # Request body
    body = {
        'Keywords': 'STM32F407VGT6',
        'Limit': 5,
        'Offset': 0
    }

    try:
        response = requests.post(search_url, headers=headers, json=body, timeout=10)

        if response.status_code == 200:
            data = response.json()
            products = data.get('Products', [])
            exact_matches = data.get('ExactMatches', [])
            total_count = data.get('ProductsCount', 0)

            log_success(f"Search successful! Found {total_count} total matches")

            if exact_matches:
                log_info(f"  Exact matches: {len(exact_matches)}")
                for i, product in enumerate(exact_matches[:3], 1):
                    digikey_pn = product.get('DigiKeyProductNumber', 'N/A')
                    mpn = product.get('ManufacturerProductNumber', 'N/A')
                    mfr = product.get('Manufacturer', {}).get('Name', 'N/A')
                    qty = product.get('QuantityAvailable', 0)
                    print(f"    {i}. {digikey_pn} - {mpn} ({mfr}) - Stock: {qty}")

            if products and not exact_matches:
                log_info(f"  Similar matches: {len(products)}")
                for i, product in enumerate(products[:3], 1):
                    digikey_pn = product.get('DigiKeyProductNumber', 'N/A')
                    mpn = product.get('ManufacturerProductNumber', 'N/A')
                    mfr = product.get('Manufacturer', {}).get('Name', 'N/A')
                    qty = product.get('QuantityAvailable', 0)
                    print(f"    {i}. {digikey_pn} - {mpn} ({mfr}) - Stock: {qty}")

            return True

        elif response.status_code == 401:
            log_error("Authentication failed (401 Unauthorized)")
            log_error("Your Client ID or access token may be invalid")
            log_error(f"Response: {response.text}")
            return False

        elif response.status_code == 429:
            log_warning("Rate limit exceeded (429 Too Many Requests)")
            log_info("Wait a moment and try again")
            return False

        else:
            log_error(f"Search failed: HTTP {response.status_code}")
            log_error(f"Response: {response.text}")
            return False

    except Exception as e:
        log_error(f"Exception during search: {str(e)}")
        return False


def main():
    """Main test function"""
    print("=" * 60)
    print("Digikey API Authentication Test")
    print("=" * 60)
    print()

    # Step 1: Load credentials
    log_info("Step 1: Loading credentials from .env...")
    client_id, client_secret = load_credentials()

    if not client_id or not client_secret:
        log_error("Missing credentials!")
        log_error("Please add to your .env file:")
        log_error("  DIGIKEY_CLIENT_ID=your_client_id")
        log_error("  DIGIKEY_CLIENT_SECRET=your_client_secret")
        return False

    log_success(f"Client ID: {client_id[:10]}...{client_id[-4:]}")
    log_success(f"Client Secret: {'*' * 20}")
    print()

    # Step 2: Get access token
    log_info("Step 2: Getting OAuth2 access token...")
    access_token = get_access_token(client_id, client_secret)

    if not access_token:
        log_error("Failed to get access token!")
        log_error("Check your credentials and try again")
        return False

    log_success(f"Access token: {access_token[:20]}...")
    print()

    # Step 3: Test search
    log_info("Step 3: Testing search API...")
    success = test_search(access_token, client_id)

    print()
    print("=" * 60)
    if success:
        log_success("ALL TESTS PASSED!")
        log_info("Your Digikey API credentials are working correctly.")
        log_info("You can now use the Digikey supplier in the GUI.")
    else:
        log_error("TESTS FAILED")
        log_info("Check the errors above and verify your credentials.")
    print("=" * 60)

    return success


if __name__ == "__main__":
    main()
