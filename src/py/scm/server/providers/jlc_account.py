"""Read-only, bounded JLC My Parts Lib adapter."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Protocol

from scm.contract_codec import DEFAULT_MAX_BYTES

STOCK_BUCKETS = (
    ("jlcpcb_parts", "jlcpcbParts"),
    ("global_sourcing_parts", "globalSourcingParts"),
    ("consigned_parts", "consignedParts"),
    ("idle_stock", "idleStock"),
)
MAX_SCAN_PAGES = 100
MAX_SCAN_SECONDS = 25.0
PAGE_SIZE = 30
# Leave room for the response envelope and JSON framing in the 8 MiB codec cap.
MAX_SCAN_BYTES = DEFAULT_MAX_BYTES - 1024 * 1024


class IncompleteInventoryScan(RuntimeError):
    """The bounded live scan could not establish a complete observation."""


class PrivateLibraryClient(Protocol):
    def get_private_component_library(
        self, *, page: int, page_size: int, timeout_seconds: float | None = None
    ) -> list[dict[str, Any]]: ...


class JLCAccountInventory:
    """Normalize JLC private-library pages without combining source balances."""

    def __init__(self, client: PrivateLibraryClient) -> None:
        self.client = client

    def page(
        self, number: int, *, timeout_seconds: float | None = None
    ) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
        rows = self.client.get_private_component_library(
            page=number, page_size=PAGE_SIZE, timeout_seconds=timeout_seconds
        )
        observed_at = datetime.now(timezone.utc).isoformat()
        if not isinstance(rows, list):
            raise ValueError("JLC private-library page was not a list.")
        if len(rows) > PAGE_SIZE:
            raise ValueError("JLC private-library page exceeded the requested size.")
        items = [self._record(row, observed_at) for row in rows]
        codes = [item["supplier_part_number"] for item in items]
        if len(codes) != len(set(codes)):
            raise ValueError("JLC private-library page repeated a C-code.")
        return items, tuple(sorted(codes))

    def scan(self) -> dict[str, Any]:
        """Read the complete observed library within time, page, and byte limits."""
        items: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        previous_codes: tuple[str, ...] = ()
        size_bytes = 0
        started = time.monotonic()
        for number in range(1, MAX_SCAN_PAGES + 1):
            remaining = MAX_SCAN_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise IncompleteInventoryScan("Inventory scan time limit reached.")
            page_items, codes = self.page(number, timeout_seconds=min(20.0, remaining))
            if number > 1 and codes == previous_codes:
                break  # JLC repeats its final full page after exhaustion.
            if seen_codes.intersection(codes):
                raise IncompleteInventoryScan("Inventory pages repeated a C-code.")
            seen_codes.update(codes)
            previous_codes = codes
            size_bytes += len(json.dumps(page_items, separators=(",", ":")).encode("utf-8"))
            if size_bytes > MAX_SCAN_BYTES:
                raise IncompleteInventoryScan("Inventory scan size limit reached.")
            items.extend(page_items)
            if len(page_items) < PAGE_SIZE:
                break
        else:
            raise IncompleteInventoryScan("Inventory scan page limit reached.")
        return {"items": items, "observed_at": datetime.now(timezone.utc).isoformat()}

    def lookup(self, *, spn: str | None = None, mpn: str | None = None) -> dict[str, Any]:
        expected = (spn or mpn or "").strip().casefold()
        result = self.scan()
        field = "supplier_part_number" if spn is not None else "manufacturer_part_number"
        matches = [
            item for item in result["items"] if (item[field] or "").strip().casefold() == expected
        ]
        return {
            "status": "observed" if matches else "not_observed",
            "items": matches,
            "observed_at": result["observed_at"],
        }

    @staticmethod
    def _record(row: Any, observed_at: str) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise ValueError("JLC private-library row was not an object.")
        code = row.get("componentCode")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("JLC private-library row has no C-code.")

        def optional_text(key: str) -> str | None:
            value = row.get(key)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError("JLC private-library text field was malformed.")
            return value.strip() or None

        balances = {}
        for field, source in STOCK_BUCKETS:
            value = row.get(source)
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
                or value > 9_007_199_254_740_991
            ):
                raise ValueError("JLC private-library balance was malformed.")
            balances[field] = value

        return {
            "supplier_part_number": code.strip(),
            "manufacturer_part_number": optional_text("componentModel"),
            "manufacturer": optional_text("componentBrandEn"),
            "description": optional_text("componentSpecification"),
            "observed_at": observed_at,
            "balances": balances,
        }
