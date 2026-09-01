"""Executable proof that served routes use the generated TypeSpec boundary."""

import json
from pathlib import Path

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scm import __version__
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
OPENAPI_PATH = CATALOG_PATH.with_name("openapi.json")


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


def test_served_stream_openapi_matches_legacy_typespec_authority():
    served_openapi = app.openapi()
    operation = served_openapi["paths"]["/v1/search/stream"]["get"]
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    authority = next(
        endpoint for endpoint in catalog["endpoints"] if endpoint["path"] == "/v1/search/stream"
    )

    assert operation["security"] == authority["security"] == [{"LegacyQueryTokenAuth": []}]
    security = served_openapi["components"]["securitySchemes"]["LegacyQueryTokenAuth"]
    assert security == {
        "type": "apiKey",
        "description": (
            "Deprecated v1 query-token compatibility surface. Never place a real service token "
            "in this query, Swagger operation, logs, or shared URLs."
        ),
        "in": "query",
        "name": "token",
    }
    assert operation["deprecated"] is True
    assert "Never place a real service token" in operation["description"]
    assert operation["x-scm-event-roots"] == authority["event_roots"] == [
        "StreamSearchEvent"
    ]
    assert set(operation["responses"]) == set(authority["responses"])
    assert set(operation["responses"]["200"]["content"]) == {"text/event-stream"}
    for status in ("400", "401", "422"):
        content = operation["responses"][status]["content"]
        assert set(content) == {"application/json"}
        assert content["application/json"]["schema"]["title"] == authority["responses"][status][0]

    max_results = next(
        parameter for parameter in operation["parameters"] if parameter["name"] == "max_results"
    )["schema"]
    assert "minimum" not in max_results
    assert "maximum" not in max_results


def test_openapi_explorers_and_documentation_match_typespec_authority():
    """Keep runtime explorers useful without creating a second documentation contract."""

    client = TestClient(app)
    for path, content_type in (
        ("/docs", "text/html"),
        ("/docs/typespec", "text/html"),
        ("/redoc", "text/html"),
        ("/openapi.json", "application/json"),
        ("/openapi-typespec.json", "application/json"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(content_type)

    served = client.get("/openapi.json").json()
    canonical = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert client.get("/openapi-typespec.json").json() == canonical
    assert served["openapi"] == canonical["openapi"] == "3.1.0"
    assert served["info"]["version"] == canonical["info"]["version"] == __version__
    assert set(served["paths"]) == set(canonical["paths"])

    for document in (served, canonical):
        status_response = document["paths"]["/v1/"]["get"]["responses"]["200"]
        assert set(status_response["content"]) == {"text/html"}
        assert "content_type" not in status_response.get("headers", {})

    for path, canonical_path in canonical["paths"].items():
        for method in {"get", "post", "put", "patch", "delete"} & set(canonical_path):
            canonical_operation = canonical_path[method]
            served_operation = served["paths"][path][method]
            assert served_operation["summary"] == canonical_operation["summary"]
            assert _normalized(served_operation["description"]) == _normalized(
                canonical_operation["description"]
            )
            assert served_operation.get("deprecated", False) == canonical_operation.get(
                "deprecated", False
            )

    warning = "Never place a real service token"
    for document in (served, canonical):
        legacy = document["paths"]["/v1/search/stream"]["get"]
        assert legacy["deprecated"] is True
        assert warning in legacy["description"]
        assert warning in document["components"]["securitySchemes"][
            "LegacyQueryTokenAuth"
        ]["description"]


def _normalized(value: str) -> str:
    return " ".join(value.split())


def test_deployed_query_integers_remain_unbounded():
    above_i_json_max = 9_007_199_254_740_992
    with (
        patch("scm.server.auth.settings") as auth_settings,
        patch("scm.server.settings.settings") as service_settings,
    ):
        auth_settings.service_token = "contract-test-token"
        service_settings.service_token = "contract-test-token"
        client = TestClient(app)
        response = client.get(
            "/v1/search",
            params={
                "supplier": "unknown",
                "mpn": "X",
                "max_results": above_i_json_max,
            },
            headers={"Authorization": "Bearer contract-test-token"},
        )
        assert response.status_code == 200

        stream_response = client.get(
            "/v1/search/stream",
            params={
                "mpn": "ABC",
                "token": "contract-test-token",
                "max_results": above_i_json_max,
                "suppliers": "unknown",
            },
        )
        assert stream_response.status_code == 400
        assert stream_response.headers["content-type"].startswith("application/json")


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
