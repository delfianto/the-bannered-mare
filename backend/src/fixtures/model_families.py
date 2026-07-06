"""Type definitions for model family seed data and parameter schemas."""

from typing import Any, Literal, NotRequired, TypedDict


class NumericParameterSchema(TypedDict):
    """Schema for numeric parameters (int, float)"""

    type: Literal["int", "float"]
    default: NotRequired[int | float]
    min_value: NotRequired[int | float]
    max_value: NotRequired[int | float]


class StringParameterSchema(TypedDict):
    """Schema for string parameters"""

    type: Literal["string"]
    default: NotRequired[str]


class BooleanParameterSchema(TypedDict):
    """Schema for boolean parameters"""

    type: Literal["boolean"]
    default: NotRequired[bool]


class EnumParameterSchema(TypedDict):
    """Schema for enum parameters (string with predefined values)"""

    type: Literal["enum"]
    default: NotRequired[str]
    str_values: list[str]


class ListParameterSchema(TypedDict):
    """Schema for list parameters (e.g. list of strings or objects)"""

    type: Literal["list"]
    default: NotRequired[list[Any]]
    item_schema: ParameterSchema


class ObjectParameterSchema(TypedDict):
    """Schema for object/dict parameters"""

    type: Literal["object"]
    default: NotRequired[dict[str, Any]]
    properties: NotRequired[dict[str, ParameterSchema]]


class JsonParameterSchema(TypedDict):
    """Schema for raw JSON parameters (e.g. response_format)"""

    type: Literal["json"]
    default: NotRequired[dict[str, Any] | None]


ParameterSchema = (
    NumericParameterSchema
    | StringParameterSchema
    | BooleanParameterSchema
    | EnumParameterSchema
    | ListParameterSchema
    | ObjectParameterSchema
    | JsonParameterSchema
)


class ModelFamilySeedData(TypedDict):
    """Type definition for model family seed data"""

    name: str
    family_identifier: str
    description: str | None
    provider_types: list[str]
    parameters: dict[str, ParameterSchema]
    unsupported_parameters: NotRequired[list[str]]
    extra_metadata: dict[str, Any] | None
