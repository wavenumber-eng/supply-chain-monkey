"""
Simple command-line test for parallel supplier search.

Tests parallel search performance without GUI.
Good for quick testing and benchmarking.

Usage:
    uv run python tests/scripts/demo_parallel_search.py
"""

import logging
import os
import threading
import time

from scm.server.providers import SupplierType, create_supplier, get_available_suppliers

log = logging.getLogger(__name__)

# Test part
TEST_MPN = "TPS543620RPYR"

def search_supplier(supplier_type, mpn, results_dict):
    """Search a single supplier (runs in thread)"""
    try:
        # Get credentials
        credentials = {}
        if supplier_type == SupplierType.DIGIKEY:
            client_id = os.environ.get("DIGIKEY_CLIENT_ID")
            client_secret = os.environ.get("DIGIKEY_CLIENT_SECRET")
            if not client_id or not client_secret:
                log.error(f"[{supplier_type.value}] Skipped - missing Digikey credentials")
                return
            credentials = {'client_id': client_id, 'client_secret': client_secret}

        log.info(f"[{supplier_type.value}] Searching...")

        supplier = create_supplier(supplier_type, **credentials)
        start_time = time.time()
        parts = supplier.search_by_mpn(mpn)
        elapsed = time.time() - start_time

        results_dict[supplier_type] = {
            'parts': parts,
            'time': elapsed,
            'error': None
        }

        log.info(f"[{supplier_type.value}] Found {len(parts)} result(s) in {elapsed:.2f}s")

    except Exception as e:
        results_dict[supplier_type] = {
            'parts': [],
            'time': 0,
            'error': str(e)
        }
        log.error(f"[{supplier_type.value}] Error: {e}")

def main():
    print("=" * 70)
    print("PARALLEL SUPPLIER SEARCH TEST")
    print("=" * 70)
    print()
    print(f"Searching for MPN: {TEST_MPN}")
    print()

    # Get available suppliers
    suppliers = get_available_suppliers()
    print(f"Available suppliers: {[s.value for s in suppliers]}")
    print()

    # Parallel search
    print("Starting parallel search...")
    print("-" * 70)

    results = {}
    threads = []

    start_time = time.time()

    # Launch threads
    for supplier_type in suppliers:
        thread = threading.Thread(
            target=search_supplier,
            args=(supplier_type, TEST_MPN, results),
            daemon=True
        )
        threads.append(thread)
        thread.start()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    total_time = time.time() - start_time

    print("-" * 70)
    print()

    # Results summary
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print()

    total_parts = 0
    for supplier_type in suppliers:
        if supplier_type not in results:
            continue

        result = results[supplier_type]
        if result['error']:
            print(f"{supplier_type.value:10s}: ERROR - {result['error']}")
        else:
            parts = result['parts']
            total_parts += len(parts)
            print(f"{supplier_type.value:10s}: {len(parts)} result(s) in {result['time']:.2f}s")

            # Show first part number
            if parts:
                print(f"            Part #: {parts[0].supplier_part_number}")

    print()
    print(f"Total search time: {total_time:.2f}s (parallel)")
    print(f"Total parts found: {total_parts}")
    print()

    # Calculate sequential time
    sequential_time = sum(r['time'] for r in results.values() if not r['error'])
    if sequential_time > 0:
        speedup = sequential_time / total_time
        print(f"Sequential time would be: {sequential_time:.2f}s")
        print(f"Speedup: {speedup:.1f}x faster")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
