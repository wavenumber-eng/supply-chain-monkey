"""Bounded JLC account inventory scans and HTTP behavior."""

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
import pytest
from fastapi.testclient import TestClient

from scm.server.main import app
from scm.server.providers import jlc_account
from scm.server.providers.jlc_account import IncompleteInventoryScan, JLCAccountInventory
from scm.server.providers.jlc_openapi import JLCOpenAPIClient, JLCOpenAPIRequestError
from scm.server.routers import account


def _row(code: str, model: str = "MODEL") -> dict:
    return {
        "componentCode": code,
        "componentModel": model,
        "componentBrandEn": "Maker",
        "componentSpecification": "Part",
        "jlcpcbParts": 3,
        "globalSourcingParts": None,
        "consignedParts": 0,
        "idleStock": 2,
    }


class _Jlc:
    def __init__(self, pages: list[list[dict]]):
        self.pages = pages
        self.calls = 0

    def get_private_component_library(
        self, *, page: int, page_size: int, timeout_seconds: float | None = None
    ) -> list[dict]:
        assert page_size == 30
        self.calls += 1
        return self.pages[min(page - 1, len(self.pages) - 1)]


def test_scan_and_lookup_preserve_four_nullable_balances():
    provider = _Jlc([[_row("C1"), _row("C2")]])
    adapter = JLCAccountInventory(provider)
    result = adapter.scan()
    assert [item["supplier_part_number"] for item in result["items"]] == ["C1", "C2"]
    assert result["items"][0]["balances"] == {
        "jlcpcb_parts": 3,
        "global_sourcing_parts": None,
        "consigned_parts": 0,
        "idle_stock": 2,
    }
    assert adapter.lookup(mpn="model")["status"] == "observed"
    assert len(adapter.lookup(mpn="model")["items"]) == 2
    assert adapter.lookup(spn="C9")["status"] == "not_observed"
    assert provider.calls == 4  # One JLC call per scan, including each lookup.


def test_exact_full_final_page_is_not_returned_twice():
    provider = _Jlc([[_row(f"C{number}") for number in range(30)]])
    result = JLCAccountInventory(provider).scan()
    assert len(result["items"]) == 30
    assert provider.calls == 2  # JLC repeats the last full page.


def test_scan_rejects_duplicate_across_pages_and_byte_overrun(monkeypatch):
    first = [_row(f"C{number}") for number in range(30)]
    second = [_row("C0"), *[_row(f"D{number}") for number in range(29)]]
    with pytest.raises(IncompleteInventoryScan, match="repeated a C-code"):
        JLCAccountInventory(_Jlc([first, second])).scan()
    monkeypatch.setattr(jlc_account, "MAX_SCAN_BYTES", 1)
    with pytest.raises(IncompleteInventoryScan, match="size limit"):
        JLCAccountInventory(_Jlc([[_row("C1")]])).scan()


def test_http_uses_service_token_and_has_no_paging(monkeypatch):
    monkeypatch.setattr(account.settings, "service_token", "service-test")
    monkeypatch.setattr(account, "_adapter", lambda: JLCAccountInventory(_Jlc([[_row("C1")]])))
    client = TestClient(app)
    path = "/v1/account/inventory"
    assert client.get(path).status_code != 200
    assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    headers = {"Authorization": "Bearer service-test"}
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    assert [item["supplier_part_number"] for item in response.json()["items"]] == ["C1"]
    assert set(response.json()) == {"items", "observed_at"}
    assert client.get("/v1/account/inventory/lookup", headers=headers).status_code == 400
    assert client.get("/v1/account/inventory/lookup", params={"spn": "C1"}, headers=headers).json()["status"] == "observed"
    operations = client.get("/openapi.json").json()["paths"]
    assert not operations[path]["get"].get("parameters")
    assert {"401", "422", "500", "502", "503"} <= set(
        operations[path]["get"]["responses"]
    )
    assert "503" not in operations["/v1/account/capabilities"]["get"]["responses"]


def test_http_returns_incomplete_when_scan_exceeds_route_deadline(monkeypatch):
    class SlowAdapter:
        def scan(self):
            time.sleep(0.05)
            return {"items": [], "observed_at": "2026-11-07T12:00:00Z"}

    monkeypatch.setattr(account.settings, "service_token", "service-test")
    monkeypatch.setattr(account, "_adapter", SlowAdapter)
    monkeypatch.setattr(account, "MAX_SCAN_SECONDS", 0.005)
    response = TestClient(app).get(
        "/v1/account/inventory", headers={"Authorization": "Bearer service-test"}
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Inventory scan is incomplete"


def test_private_library_response_is_bounded(monkeypatch):
    class TooLargeResponse:
        status_code = 200

        def iter_content(self, *, chunk_size: int):
            yield b"x" * 2_000_001

        def close(self):
            pass

    monkeypatch.setattr(
        "scm.server.providers.jlc_openapi.requests.post",
        lambda *args, **kwargs: TooLargeResponse(),
    )
    with pytest.raises(JLCOpenAPIRequestError, match="size limit"):
        JLCOpenAPIClient(app_id="a", access_key="b", secret_key="c").get_private_component_library()


def test_private_library_allows_more_than_two_seconds_to_first_byte():
    class SlowFirstByte(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(2.25)
            body = b'{"code":200,"success":true,"data":[]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), SlowFirstByte) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}"
            client = JLCOpenAPIClient(app_id="a", access_key="b", secret_key="c", endpoint=endpoint)
            assert client.get_private_component_library(timeout_seconds=10.0) == []
        finally:
            server.shutdown()
            thread.join()


def test_non_json_existing_jlc_call_keeps_path_and_status(monkeypatch):
    response = requests.Response()
    response.status_code = 502
    response._content = b"not json"
    monkeypatch.setattr("scm.server.providers.jlc_openapi.requests.post", lambda *args, **kwargs: response)
    with pytest.raises(JLCOpenAPIRequestError, match=r"getComponentInfos.*not valid JSON.*status 502"):
        JLCOpenAPIClient(app_id="a", access_key="b", secret_key="c").get_component_infos()
