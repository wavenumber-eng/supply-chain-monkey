#!/usr/bin/env python3
"""
supply-chain-monkey test CLI

Exercises service endpoints against a local or remote instance.

Usage:
    # Test local dev server
    python tests/scripts/scm_test_cli.py

    # Test remote deployment
    python tests/scripts/scm_test_cli.py --url https://your-app.appliku.com --token YOUR_TOKEN

    # Test specific provider
    python tests/scripts/scm_test_cli.py --provider jlcpcb

    # Test with a specific MPN
    python tests/scripts/scm_test_cli.py --mpn STM32F407VGT6
"""

import argparse
import json
import sys
import time

import requests


def run_test(name, fn):
    """Run a test function, print result."""
    try:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        return ok
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test supply-chain-monkey service")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Service base URL")
    parser.add_argument("--token", default="test123", help="Bearer token")
    parser.add_argument("--mpn", default="TPS543620RPYR", help="MPN to search for")
    parser.add_argument("--provider", default=None, help="Test only this provider")
    parser.add_argument("--detail-code", default=None, help="C-code or part number for detail test")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    headers = {"Authorization": f"Bearer {args.token}"}
    providers = [args.provider] if args.provider else ["jlcpcb", "lcsc", "digikey", "mouser"]
    passed = 0
    failed = 0

    print(f"Testing: {base}")
    print(f"MPN: {args.mpn}")
    print()

    # --- Health ---
    print("Health:")

    def test_health():
        r = requests.get(f"{base}/v1/health", timeout=10)
        return r.status_code == 200 and r.json().get("status") == "ok", f"{r.status_code}"

    if run_test("GET /v1/health (no auth)", test_health):
        passed += 1
    else:
        failed += 1

    # --- Auth ---
    print("\nAuth:")

    def test_no_token():
        r = requests.get(f"{base}/v1/providers/status", timeout=10)
        return r.status_code == 422, f"{r.status_code}"

    def test_bad_token():
        r = requests.get(f"{base}/v1/providers/status", headers={"Authorization": "Bearer wrong"}, timeout=10)
        return r.status_code == 401, f"{r.status_code}"

    def test_good_token():
        r = requests.get(f"{base}/v1/providers/status", headers=headers, timeout=10)
        return r.status_code == 200, f"{r.status_code}"

    for t in [test_no_token, test_bad_token, test_good_token]:
        if run_test(t.__name__.replace("test_", ""), t):
            passed += 1
        else:
            failed += 1

    # --- Provider status ---
    print("\nProvider status:")

    def test_providers_status():
        r = requests.get(f"{base}/v1/providers/status", headers=headers, timeout=10)
        data = r.json()
        providers_info = data.get("providers", {})
        configured = [k for k, v in providers_info.items() if v.get("configured")]
        return len(configured) > 0, f"configured: {', '.join(configured)}"

    if run_test("providers configured", test_providers_status):
        passed += 1
    else:
        failed += 1

    # --- Search per provider ---
    print(f"\nSearch (mpn={args.mpn}):")

    for provider in providers:
        def test_search(p=provider):
            t0 = time.monotonic()
            r = requests.get(
                f"{base}/v1/search",
                params={"supplier": p, "mpn": args.mpn},
                headers=headers,
                timeout=30,
            )
            latency = int((time.monotonic() - t0) * 1000)
            body = r.json()
            status = body.get("status")
            count = len(body.get("data") or [])
            server_ms = body.get("provider_latency_ms", "?")

            if status == "ok":
                first = body["data"][0]
                return True, (
                    f"{count} result(s), {first['supplier_part_number']}, "
                    f"stock={first['stock_quantity']} ({first['stock_status']}), "
                    f"server={server_ms}ms, total={latency}ms"
                )
            elif status == "not_found":
                return True, f"no results (server={server_ms}ms, total={latency}ms)"
            elif status == "provider_error":
                return False, f"error: {body.get('error', '?')}"
            else:
                return False, f"unexpected status: {status}"

        if run_test(f"search {provider}", test_search):
            passed += 1
        else:
            failed += 1

    # --- Detail (JLCPCB C-code) ---
    detail_code = args.detail_code or "C2870085"
    detail_provider = args.provider or "jlcpcb"

    print(f"\nDetail (part={detail_code}, supplier={detail_provider}):")

    def test_detail():
        t0 = time.monotonic()
        r = requests.get(
            f"{base}/v1/detail",
            params={"supplier": detail_provider, "part": detail_code},
            headers=headers,
            timeout=30,
        )
        latency = int((time.monotonic() - t0) * 1000)
        body = r.json()
        status = body.get("status")
        server_ms = body.get("provider_latency_ms", "?")

        if status == "ok":
            d = body["data"]
            return True, (
                f"{d['supplier_part_number']}, mpn={d['manufacturer_part_number']}, "
                f"stock={d['stock_quantity']} ({d['stock_status']}), "
                f"server={server_ms}ms, total={latency}ms"
            )
        elif status == "not_found":
            return True, f"not found (server={server_ms}ms)"
        else:
            return False, f"error: {body.get('error', '?')}"

    if run_test(f"detail {detail_provider}/{detail_code}", test_detail):
        passed += 1
    else:
        failed += 1

    # --- Unknown supplier ---
    print("\nEdge cases:")

    def test_unknown_supplier():
        r = requests.get(
            f"{base}/v1/search",
            params={"supplier": "fakesupplier", "mpn": "X"},
            headers=headers,
            timeout=10,
        )
        body = r.json()
        return body["status"] == "provider_error", body.get("error", "")

    if run_test("unknown supplier", test_unknown_supplier):
        passed += 1
    else:
        failed += 1

    # --- Summary ---
    total = passed + failed
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
