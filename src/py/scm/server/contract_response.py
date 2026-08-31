"""Generated-model and authoritative-schema response boundary."""

from typing import TypeVar, cast

from pydantic import BaseModel

from scm.contract_codec import encode


ContractModel = TypeVar("ContractModel", bound=BaseModel)


def contract_response(
    root: str,
    model_type: type[ContractModel],
    value: BaseModel | dict,
) -> ContractModel:
    """Project a service value into a generated model and schema-check its JSON."""

    document = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    instance = model_type.model_validate(document)
    encode(root, instance)
    return cast(ContractModel, instance)


def contract_json(root: str, value: BaseModel | dict) -> str:
    """Encode a generated contract root as strict schema-validated JSON."""

    return encode(root, value).decode("utf-8")
