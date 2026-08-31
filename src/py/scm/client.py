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

    # Canonical exact supplier part number lookup
    result = client.spn("jlcpcb", "C2870085")

    # Enumerate suppliers
    from scm.models import SUPPLIERS, SupplierType, PARAMETER_FIELD_NAMES
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from .contract_codec import DEFAULT_MAX_BYTES, PayloadTooLargeError, decode, encode
from .models import (
    SUPPLIERS,
    DetailEnvelope,
    HealthResponse,
    ProviderStatusResponse,
    SearchEnvelope,
    ServiceEnvelope,
    SpnBatchEnvelope,
    SpnBatchRequest,
    SpnEnvelope,
)


_RESPONSE_CHUNK_BYTES = 64 * 1024


class SCMClient:
    """HTTP client for the supply-chain-monkey API."""

    def __init__(
        self,
        url: str,
        token: str,
        timeout: float = 30.0,
        max_response_bytes: int = DEFAULT_MAX_BYTES,
    ):
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _get(self, url: str, **kwargs):
        return requests.get(url, **kwargs)

    def _post(self, url: str, **kwargs):
        return requests.post(url, **kwargs)

    def _response_bytes(self, response: Any) -> bytes:
        headers = getattr(response, "headers", {})
        content_length = headers.get("content-length") if headers else None
        if content_length is not None:
            try:
                if int(content_length) > self.max_response_bytes:
                    raise PayloadTooLargeError(
                        f"response exceeds the {self.max_response_bytes}-byte limit"
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        size = 0
        if hasattr(response, "iter_content"):
            iterator = response.iter_content(chunk_size=_RESPONSE_CHUNK_BYTES)
        else:
            iterator = (response.content,)
        for chunk in iterator:
            if not chunk:
                continue
            size += len(chunk)
            if size > self.max_response_bytes:
                raise PayloadTooLargeError(
                    f"response exceeds the {self.max_response_bytes}-byte limit"
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _request_model(self, method: str, path: str, root: str, **kwargs):
        request = self._get if method == "GET" else self._post
        response = request(
            f"{self.url}{path}",
            timeout=self.timeout,
            stream=True,
            **kwargs,
        )
        try:
            response.raise_for_status()
            return decode(
                root,
                self._response_bytes(response),
                max_bytes=self.max_response_bytes,
            )
        finally:
            if hasattr(response, "close"):
                response.close()

    @staticmethod
    def _legacy_envelope(model) -> ServiceEnvelope:
        return ServiceEnvelope.model_validate(model.model_dump(mode="json"))

    def health(self) -> dict:
        """Check service health. No auth required."""
        result = self._request_model("GET", "/v1/health", "HealthResponse")
        assert isinstance(result, HealthResponse)
        return result.model_dump(mode="json")

    def providers_status(self) -> dict:
        """Get provider configuration status."""
        result = self._request_model(
            "GET",
            "/v1/providers/status",
            "ProviderStatusResponse",
            headers=self._headers(),
        )
        assert isinstance(result, ProviderStatusResponse)
        return result.model_dump(mode="json", exclude_unset=True)

    def search(self, supplier: str, mpn: str, *, include_raw: bool = False) -> ServiceEnvelope:
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

        result = self._request_model(
            "GET",
            "/v1/search",
            "SearchEnvelope",
            params=params,
            headers=self._headers(),
        )
        assert isinstance(result, SearchEnvelope)
        return self._legacy_envelope(result)

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
                pool.submit(self.search, s, mpn, include_raw=include_raw): s for s in targets
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

    def detail(self, supplier: str, part: str, *, include_raw: bool = False) -> ServiceEnvelope:
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

        result = self._request_model(
            "GET",
            "/v1/detail",
            "DetailEnvelope",
            params=params,
            headers=self._headers(),
        )
        assert isinstance(result, DetailEnvelope)
        return self._legacy_envelope(result)

    def spn(self, supplier: str, spn: str, *, include_raw: bool = False) -> ServiceEnvelope:
        """Get detail for an exact supplier part number.

        Args:
            supplier: Supplier name (jlcpcb, lcsc, digikey, mouser)
            spn: Exact supplier part number
            include_raw: Include extra_data in response

        Returns:
            ServiceEnvelope with part detail
        """
        params = {"supplier": supplier, "spn": spn}
        if include_raw:
            params["include_raw"] = "true"

        result = self._request_model(
            "GET",
            "/v1/spn",
            "SpnEnvelope",
            params=params,
            headers=self._headers(),
        )
        assert isinstance(result, SpnEnvelope)
        return self._legacy_envelope(result)

    def spn_batch(
        self, supplier: str, spns: list[str], *, include_raw: bool = False
    ) -> ServiceEnvelope:
        """Get detail for multiple exact supplier part numbers."""
        payload = encode(
            "SpnBatchRequest",
            SpnBatchRequest(
                supplier=supplier,
                spns=spns,
                include_raw=include_raw,
            ),
        )
        headers = {**self._headers(), "Content-Type": "application/json"}
        result = self._request_model(
            "POST",
            "/v1/spn/batch",
            "SpnBatchEnvelope",
            data=payload,
            headers=headers,
        )
        assert isinstance(result, SpnBatchEnvelope)
        return self._legacy_envelope(result)
