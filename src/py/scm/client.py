"""
SCM HTTP client for querying the supply-chain-monkey service.

Usage:
    from scm.client import SCMClient

    client = SCMClient(url="https://your-scm.example.com", token="your-token")

    # Search one supplier
    result = client.search("jlcpcb", "TPS543620RPYR")

    # Search all suppliers in parallel
    all_results = client.search_all("TPS543620RPYR")

    # Get detail for a specific part
    detail = client.detail("jlcpcb", "C2870085")

    # Enumerate suppliers
    from scm.models import SUPPLIERS, SupplierType, PARAMETER_FIELD_NAMES
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .models import (
    SUPPLIERS,
    ServiceEnvelope,
)


class SCMClient:
    """HTTP client for the supply-chain-monkey API."""

    def __init__(self, url: str, token: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def health(self) -> dict:
        """Check service health. No auth required."""
        r = requests.get(f"{self.url}/v1/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def providers_status(self) -> dict:
        """Get provider configuration status."""
        r = requests.get(
            f"{self.url}/v1/providers/status",
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def search(
        self, supplier: str, mpn: str, *, include_raw: bool = False
    ) -> ServiceEnvelope:
        """Search a single supplier by MPN.

        Args:
            supplier: Supplier name (jlcpcb, lcsc, digikey, mouser)
            mpn: Manufacturer part number
            include_raw: Include extra_data in response

        Returns:
            ServiceEnvelope with search results
        """
        params = {"supplier": supplier, "mpn": mpn}
        if include_raw:
            params["include_raw"] = "true"

        r = requests.get(
            f"{self.url}/v1/search",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return ServiceEnvelope(**r.json())

    def search_all(
        self, mpn: str, *, suppliers: list[str] | None = None, include_raw: bool = False
    ) -> dict[str, ServiceEnvelope]:
        """Search all (or specified) suppliers in parallel.

        Args:
            mpn: Manufacturer part number
            suppliers: List of supplier names to search. Defaults to all.
            include_raw: Include extra_data in responses

        Returns:
            Dict of {supplier_name: ServiceEnvelope}
        """
        targets = suppliers or SUPPLIERS
        results = {}

        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            futures = {
                pool.submit(self.search, s, mpn, include_raw=include_raw): s
                for s in targets
            }
            for future in as_completed(futures):
                supplier_name = futures[future]
                try:
                    results[supplier_name] = future.result()
                except Exception as exc:
                    results[supplier_name] = ServiceEnvelope(
                        status="provider_error",
                        supplier=supplier_name,
                        error=str(exc),
                    )

        return results

    def detail(
        self, supplier: str, part: str, *, include_raw: bool = False
    ) -> ServiceEnvelope:
        """Get detail for a specific supplier part number.

        Args:
            supplier: Supplier name (jlcpcb, lcsc, digikey, mouser)
            part: Supplier part number (e.g., C2870085, 296-xxx-ND)
            include_raw: Include extra_data in response

        Returns:
            ServiceEnvelope with part detail
        """
        params = {"supplier": supplier, "part": part}
        if include_raw:
            params["include_raw"] = "true"

        r = requests.get(
            f"{self.url}/v1/detail",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return ServiceEnvelope(**r.json())
