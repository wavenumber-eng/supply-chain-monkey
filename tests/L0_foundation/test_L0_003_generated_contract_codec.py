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
    encode,
)
from scm.generated.v1 import models as generated_models


VECTOR_ROOT = Path(__file__).parents[2] / "contracts" / "scm" / "v1" / "vectors"
MANIFEST = json.loads((VECTOR_ROOT / "manifest.a0.json").read_text(encoding="utf-8"))


def _case(case_id: str) -> dict[str, Any]:
    return next(case for case in MANIFEST["cases"] if case["id"] == case_id)


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
def test_contract_vectors_have_bound_digests_and_expected_outcomes(case):
    payload = (VECTOR_ROOT / case["path"]).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == case["sha256"]

    if case["valid"]:
        model = decode(case["schema"], payload)
        assert decode(case["schema"], encode(case["schema"], model)) == model
    else:
        with pytest.raises(ContractCodecError):
            decode(case["schema"], payload)


def test_catalog_root_inventory_has_generated_model_classes():
    catalog_path = (
        Path(generated_models.__file__).parent / "resources" / "contract_catalog.a0.json"
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for root in catalog["roots"]:
        local_name = root["name"].rsplit(".", 1)[-1]
        assert getattr(generated_models, local_name)


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
