"""Strict runtime codec for TypeSpec-generated SCM v1 contracts."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema.validators import validator_for
from pydantic import BaseModel, ValidationError as PydanticValidationError
from referencing import Registry, Resource

from scm.generated.v1 import models as generated_models

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
MIN_IJSON_INTEGER = -9_007_199_254_740_991
MAX_IJSON_INTEGER = 9_007_199_254_740_991


class ContractCodecError(ValueError):
    """Base error raised when a payload does not satisfy the wire contract."""


class PayloadTooLargeError(ContractCodecError):
    """The encoded payload exceeded the configured byte limit."""


class JsonPreflightError(ContractCodecError):
    """The payload was not valid strict I-JSON."""


class ContractSchemaError(ContractCodecError):
    """The JSON value did not satisfy the authoritative generated schema."""


class ContractModelError(ContractCodecError):
    """Schema-valid JSON could not be decoded into its generated model."""


def _reject_constant(value: str) -> None:
    raise JsonPreflightError(f"non-finite JSON number is not permitted: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonPreflightError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def _check_ijson(value: Any, path: str = "$") -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if not MIN_IJSON_INTEGER <= value <= MAX_IJSON_INTEGER:
            raise JsonPreflightError(f"integer outside the I-JSON interoperable range at {path}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JsonPreflightError(f"non-finite JSON number at {path}")
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise JsonPreflightError(f"unpaired Unicode surrogate at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_ijson(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _check_ijson(key, f"{path}.<key>")
            _check_ijson(item, f"{path}.{key}")
        return
    raise JsonPreflightError(f"unsupported JSON value at {path}: {type(value).__name__}")


def _bounded(payload: bytes, max_bytes: int) -> None:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if len(payload) > max_bytes:
        raise PayloadTooLargeError(f"payload is {len(payload)} bytes; limit is {max_bytes}")


def _loads(payload: bytes, max_bytes: int) -> Any:
    _bounded(payload, max_bytes)
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise JsonPreflightError("payload is not valid UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except JsonPreflightError:
        raise
    except json.JSONDecodeError as error:
        raise JsonPreflightError(f"invalid JSON: {error.msg}") from error
    _check_ijson(value)
    return value


@lru_cache(maxsize=1)
def _contract_data() -> tuple[dict[str, dict[str, Any]], dict[str, str], Registry]:
    root = resources.files("scm.generated.v1.resources")
    catalog = json.loads(root.joinpath("contract_catalog.a0.json").read_text(encoding="utf-8"))
    schema_root = root.joinpath("schema")
    schemas: dict[str, dict[str, Any]] = {}
    catalog_roots: dict[str, str] = {}
    registry: Registry = Registry()
    by_artifact = {entry["artifact"].rsplit("/", 1)[-1]: entry for entry in catalog["roots"]}

    for schema_file in schema_root.iterdir():
        if not schema_file.name.endswith(".json"):
            continue
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        schema_id = schema.get("$id", schema_file.name)
        registry = registry.with_resource(schema_id, resource)
        registry = registry.with_resource(schema_file.name, resource)
        registry = registry.with_resource(f"urn:{schema_file.name}", resource)
        schemas[schema_file.name.removesuffix(".json")] = schema
        schemas[schema_id] = schema
        if root_entry := by_artifact.get(schema_file.name):
            local_name = root_entry["name"].rsplit(".", 1)[-1]
            schemas[local_name] = schema
            schemas[root_entry["name"]] = schema
            schemas[root_entry["schema_id"]] = schema
            catalog_roots[local_name] = local_name
            catalog_roots[root_entry["name"]] = local_name
            catalog_roots[root_entry["schema_id"]] = local_name

    return schemas, catalog_roots, registry


def _selection(
    name: str, *, catalog_only: bool
) -> tuple[type[BaseModel], dict[str, Any], Registry]:
    schemas, catalog_roots, registry = _contract_data()
    try:
        schema = schemas[name]
    except KeyError as error:
        raise KeyError(f"unknown SCM v1 schema: {name}") from error
    if catalog_only:
        try:
            local_name = catalog_roots[name]
        except KeyError as error:
            raise KeyError(f"not an SCM v1 catalog root: {name}") from error
    else:
        local_name = name.rsplit(".", 1)[-1].removesuffix(".json")
    if name.startswith("urn:") and not catalog_only:
        local_name = next(
            name for name, candidate in schemas.items() if "." not in name and candidate is schema
        )
    model = getattr(generated_models, local_name)
    return model, schema, registry


def _validate(schema: dict[str, Any], registry: Registry, value: Any) -> None:
    validator_type = validator_for(schema)
    validator_type.check_schema(schema)
    try:
        validator_type(schema, registry=registry).validate(value)
    except JsonSchemaValidationError as error:
        location = "$" + "".join(f"[{part!r}]" for part in error.absolute_path)
        raise ContractSchemaError(f"schema validation failed at {location}: {error.message}") from error


def decode(root: str, payload: bytes, *, max_bytes: int = DEFAULT_MAX_BYTES) -> BaseModel:
    """Decode bounded strict JSON into the catalog-selected generated model."""

    value = _loads(payload, max_bytes)
    model, schema, registry = _selection(root, catalog_only=True)
    _validate(schema, registry, value)
    try:
        return model.model_validate(value)
    except PydanticValidationError as error:
        raise ContractModelError("generated model validation failed") from error


def decode_schema(name: str, payload: bytes, *, max_bytes: int = DEFAULT_MAX_BYTES) -> BaseModel:
    """Decode a named generated declaration schema outside the catalog root API."""

    value = _loads(payload, max_bytes)
    model, schema, registry = _selection(name, catalog_only=False)
    _validate(schema, registry, value)
    try:
        return model.model_validate(value)
    except PydanticValidationError as error:
        raise ContractModelError("generated model validation failed") from error


def encode(
    root: str,
    value: BaseModel | dict[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    """Validate a generated model/value against its root schema and encode it."""

    model, schema, registry = _selection(root, catalog_only=True)
    try:
        instance = value if isinstance(value, model) else model.model_validate(value)
    except PydanticValidationError as error:
        raise ContractModelError("generated model validation failed") from error
    document = instance.model_dump(mode="json", by_alias=True, exclude_unset=True)
    _check_ijson(document)
    _validate(schema, registry, document)
    try:
        payload = json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (UnicodeEncodeError, ValueError) as error:
        raise JsonPreflightError("value cannot be encoded as strict UTF-8 JSON") from error
    _bounded(payload, max_bytes)
    return payload
