import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scm.contract_codec import (
    ContractCodecError,
    ContractSchemaError,
    JsonPreflightError,
    PayloadTooLargeError,
    decode,
    decode_schema,
    encode,
)
from scm.client import SCMClient
from scm.generated.v1 import models as generated_models
from scm.models import PARAMETER_FIELD_NAMES, SUPPLIERS, ServiceEnvelope, SupplierType


VECTOR_ROOT = Path(__file__).parents[2] / "contracts" / "scm" / "v1" / "vectors"
MANIFEST = json.loads((VECTOR_ROOT / "manifest.a0.json").read_text(encoding="utf-8"))


def _case(case_id: str) -> dict[str, Any]:
    return next(case for case in MANIFEST["cases"] if case["id"] == case_id)


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
def test_contract_vectors_have_bound_digests_and_expected_outcomes(case):
    payload = (VECTOR_ROOT / case["path"]).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == case["sha256"]

    if case["valid"]:
        if case.get("catalog_root", True):
            model = decode(case["schema"], payload)
            assert decode(case["schema"], encode(case["schema"], model)) == model
        else:
            assert decode_schema(case["schema"], payload)
    else:
        with pytest.raises(ContractCodecError):
            decode(case["schema"], payload)


def test_catalog_root_inventory_has_generated_model_classes():
    catalog_path = Path(generated_models.__file__).parent / "resources" / "contract_catalog.a0.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    vector_roots = {case["schema"] for case in MANIFEST["cases"] if case.get("catalog_root", True)}
    for root in catalog["roots"]:
        local_name = root["name"].rsplit(".", 1)[-1]
        assert getattr(generated_models, local_name)
        assert local_name in vector_roots


def test_primary_codec_rejects_non_root_declaration_schemas():
    payload = (VECTOR_ROOT / _case("auth-error")["path"]).read_bytes()
    with pytest.raises(KeyError, match="not an SCM v1 catalog root"):
        decode("HttpErrorDetail", payload)
    declaration = decode_schema("HttpErrorDetail", payload)
    assert isinstance(declaration, generated_models.HttpErrorDetail)
    assert declaration.detail == "Not authenticated"


def test_codec_rejects_non_utf8_and_unpaired_surrogates():
    with pytest.raises(JsonPreflightError, match="UTF-8"):
        decode("HealthResponse", b"\xff")
    with pytest.raises(JsonPreflightError, match="surrogate"):
        decode("HealthResponse", b'{"status":"\\ud800"}')


def test_codec_enforces_input_and_output_byte_limits():
    payload = (VECTOR_ROOT / _case("health")["path"]).read_bytes()
    with pytest.raises(PayloadTooLargeError):
        decode("HealthResponse", payload, max_bytes=len(payload) - 1)
    with pytest.raises(PayloadTooLargeError):
        encode("HealthResponse", {"status": "ok"}, max_bytes=1)


def test_schema_validation_precedes_generated_model_validation():
    payload = (VECTOR_ROOT / _case("health-extra")["path"]).read_bytes()
    with pytest.raises(ContractSchemaError):
        decode("HealthResponse", payload)


def test_existing_python_client_and_public_contract_accept_shared_vectors(monkeypatch):
    payloads = {
        "/v1/health": "health",
        "/v1/providers/status": "provider-status",
        "/v1/search": "search-ok",
        "/v1/detail": "detail-ok",
        "/v1/spn": "detail-ok",
        "/v1/spn/batch": "spn-batch-partial",
    }

    class Response:
        def __init__(self, case_id: str):
            self.case_id = case_id
            self.headers = {}
            path = VECTOR_ROOT / _case(self.case_id)["path"]
            self.content = path.read_bytes()

        def raise_for_status(self):
            return None

        def close(self):
            return None

    def fake_request(url, **_kwargs):
        route = next(path for path in payloads if url.endswith(path))
        if route == "/v1/spn/batch":
            assert decode("SpnBatchRequest", _kwargs["data"])
            assert _kwargs["headers"]["Content-Type"] == "application/json"
        return Response(payloads[route])

    monkeypatch.setattr("scm.client.requests.get", fake_request)
    monkeypatch.setattr("scm.client.requests.post", fake_request)
    client = SCMClient("https://scm.example.invalid", "test-token")

    assert client.health() == {"status": "ok"}
    assert "Digikey" in client.providers_status()["providers"]
    assert isinstance(client.search("digikey", "NE555P"), ServiceEnvelope)
    assert isinstance(client.detail("lcsc", "C123"), ServiceEnvelope)
    monkeypatch.setitem(payloads, "/v1/spn", "spn-ok")
    assert isinstance(client.spn("lcsc", "C123"), ServiceEnvelope)
    assert client.spn_batch("digikey", ["one", "two"]).status == "partial"
    assert isinstance(
        client.search_all("NE555P", suppliers=["digikey"])["digikey"], ServiceEnvelope
    )

    assert SUPPLIERS == ["jlcpcb", "lcsc", "digikey", "mouser"]
    assert PARAMETER_FIELD_NAMES[SupplierType.DIGIKEY] == "Digikey Part #"


@pytest.mark.parametrize(
    ("payload", "max_bytes", "error_type"),
    [
        (b'{"status":"ok","status":"ok"}', 1024, JsonPreflightError),
        (b'{"status":"ok"}', 4, PayloadTooLargeError),
    ],
)
def test_python_client_strictly_rejects_duplicate_and_oversized_responses(
    monkeypatch, payload, max_bytes, error_type
):
    class Response:
        headers = {}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            midpoint = len(payload) // 2
            yield payload[:midpoint]
            yield payload[midpoint:]

        def close(self):
            return None

    monkeypatch.setattr("scm.client.requests.get", lambda *_args, **_kwargs: Response())
    client = SCMClient(
        "https://scm.example.invalid",
        "test-token",
        max_response_bytes=max_bytes,
    )

    with pytest.raises(error_type):
        client.health()


def test_python_client_rejects_declared_oversize_before_streaming(monkeypatch):
    class Response:
        headers = {"content-length": "1025"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            raise AssertionError("oversized declared body must not be streamed")

        def close(self):
            return None

    monkeypatch.setattr("scm.client.requests.get", lambda *_args, **_kwargs: Response())
    client = SCMClient(
        "https://scm.example.invalid",
        "test-token",
        max_response_bytes=1024,
    )

    with pytest.raises(PayloadTooLargeError):
        client.health()


def test_provider_raw_json_preserves_integer_and_fractional_number_kinds():
    payload = (VECTOR_ROOT / _case("detail-ok")["path"]).read_bytes()
    model = decode("DetailEnvelope", payload)
    assert isinstance(model, generated_models.DetailEnvelope)
    assert model.data is not None
    assert model.data.extra_data is not None
    integer_value = model.data.extra_data.root["integer_value"]
    fractional_value = model.data.extra_data.root["fractional_value"]
    assert integer_value is not None and integer_value.root == 7
    assert isinstance(integer_value.root, int)
    assert fractional_value is not None and fractional_value.root == 1.25
    assert isinstance(fractional_value.root, float)
