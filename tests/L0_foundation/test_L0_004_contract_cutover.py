"""Executable proof that served routes use the generated TypeSpec boundary."""

import json
from pathlib import Path

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scm.contract_codec import decode
from scm.models import (
    DetailEnvelope,
    HealthResponse,
    ProviderStatusResponse,
    SearchEnvelope,
    SpnBatchEnvelope,
    SpnBatchRequest,
    SpnEnvelope,
)
from scm.server.main import app


ROUTE_MODELS = {
    ("GET", "/v1/health"): HealthResponse,
    ("GET", "/v1/providers/status"): ProviderStatusResponse,
    ("GET", "/v1/search"): SearchEnvelope,
    ("GET", "/v1/detail"): DetailEnvelope,
    ("GET", "/v1/spn"): SpnEnvelope,
    ("POST", "/v1/spn/batch"): SpnBatchEnvelope,
}
CATALOG_PATH = (
    Path(__file__).parents[2]
    / "contracts"
    / "scm"
    / "v1"
    / "generated"
    / "contract_catalog.a0.json"
)


def test_fastapi_routes_and_openapi_declare_generated_roots():
    served_openapi = app.openapi()

    for key, model in ROUTE_MODELS.items():
        method, path = key
        response_schema = served_openapi["paths"][path][method.lower()]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        assert response_schema["$ref"].endswith(f"/{model.__name__}")

    request_schema = served_openapi["paths"]["/v1/spn/batch"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert request_schema["$ref"].endswith("/SpnBatchRequest")


def test_served_auth_and_error_metadata_matches_typespec_catalog():
    served_openapi = app.openapi()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_endpoints = {
        (endpoint["method"], endpoint["path"]): endpoint for endpoint in catalog["endpoints"]
    }
    security_scheme = served_openapi["components"]["securitySchemes"]["BearerAuth"]
    assert security_scheme["type"] == "http"
    assert security_scheme["scheme"].lower() == "bearer"

    for method, path in ROUTE_MODELS:
        if path == "/v1/health":
            continue
        authority = catalog_endpoints[(method, path)]
        operation = served_openapi["paths"][path][method.lower()]
        assert operation["security"] == authority["security"] == [{"BearerAuth": []}]
        assert set(operation["responses"]) == set(authority["responses"])
        parameters = operation.get("parameters", [])
        assert all(parameter["name"].lower() != "authorization" for parameter in parameters)
        for status, roots in authority["responses"].items():
            if not roots:
                continue
            schema = operation["responses"][status]["content"]["application/json"]["schema"]
            assert schema["$ref"].endswith(f"/{roots[0]}")


def test_spn_batch_optional_boolean_is_non_nullable():
    assert SpnBatchRequest(supplier="LCSC", spns=["C123"]).include_raw is False
    with pytest.raises(ValidationError):
        SpnBatchRequest.model_validate({"supplier": "LCSC", "spns": ["C123"], "include_raw": None})


def test_runtime_responses_decode_through_authoritative_schemas():
    cases = [
        ("GET", "/v1/health", "HealthResponse", None),
        ("GET", "/v1/providers/status", "ProviderStatusResponse", None),
        ("GET", "/v1/search", "SearchEnvelope", {"supplier": "unknown", "mpn": "X"}),
        ("GET", "/v1/detail", "DetailEnvelope", {"supplier": "unknown", "part": "X"}),
        ("GET", "/v1/spn", "SpnEnvelope", {"supplier": "unknown", "spn": "X"}),
    ]
    with patch("scm.server.auth.settings") as auth_settings:
        auth_settings.service_token = "contract-test-token"
        client = TestClient(app)
        headers = {"Authorization": "Bearer contract-test-token"}
        for method, path, root, params in cases:
            response = client.request(method, path, params=params, headers=headers)
            assert response.status_code == 200
            assert decode(root, response.content)

        batch = client.post(
            "/v1/spn/batch",
            json={"supplier": "unknown", "spns": ["X"]},
            headers=headers,
        )
        assert batch.status_code == 200
        assert decode("SpnBatchEnvelope", batch.content)

        nullable = client.post(
            "/v1/spn/batch",
            json={"supplier": "LCSC", "spns": ["C123"], "include_raw": None},
            headers=headers,
        )
        assert nullable.status_code == 422
