"""Validate per-model sampler parameters against a model family's schema.

Pure functions extracted from ModelService: a value dict is checked against the
family's declared ``parameters`` (type / min-max / enum) and its
``unsupported_parameters``. Raises ValidationError (HTTP 422) on the first
violation.
"""

from typing import Any

from src.core.exceptions import ValidationError
from src.model_family.models import ModelFamily

# param type -> (predicate, human description of the expected type)
_TYPE_CHECKS: dict[str, tuple[Any, str]] = {
    "int": (lambda v: isinstance(v, int), "an integer"),
    "float": (lambda v: isinstance(v, (int, float)), "a number (float/int)"),
    "string": (lambda v: isinstance(v, str), "a string"),
    "boolean": (lambda v: isinstance(v, bool), "a boolean"),
    "enum": (lambda v: isinstance(v, str), "(enum) a string"),
    "list": (lambda v: isinstance(v, list), "a list"),
    "object": (lambda v: isinstance(v, dict), "an object (dict)"),
}


def validate_single_parameter(name: str, value: Any, rule: dict[str, Any]) -> None:
    """Validate one value against a family parameter rule (type, range, enum)."""
    param_type = rule.get("type")

    check = _TYPE_CHECKS.get(param_type) if param_type else None
    if check and not check[0](value):
        raise ValidationError(f"Parameter '{name}' must be {check[1]}.")

    if param_type in ("int", "float"):
        min_value = rule.get("min_value")
        max_value = rule.get("max_value")
        if min_value is not None and value < min_value:
            raise ValidationError(f"Parameter '{name}' cannot be less than {min_value}.")
        if max_value is not None and value > max_value:
            raise ValidationError(f"Parameter '{name}' cannot be greater than {max_value}.")

    if param_type == "enum" and "str_values" in rule and value not in rule["str_values"]:
        allowed = ", ".join(map(str, rule["str_values"]))
        raise ValidationError(f"Parameter '{name}' must be one of: {allowed}.")


def validate_parameters(parameters: dict[str, Any], model_family: ModelFamily | None) -> None:
    """Validate parameter values against the family's parameter schema."""
    if not parameters or not model_family:
        return

    family_params = model_family.parameters or {}
    unsupported = model_family.unsupported_parameters or []

    for param_name, value in parameters.items():
        if param_name in unsupported:
            raise ValidationError(
                f"Parameter '{param_name}' is explicitly unsupported by model family "
                f"'{model_family.name}'."
            )
        if param_name not in family_params:
            supported = ", ".join(sorted(family_params.keys()))
            raise ValidationError(
                f"Parameter '{param_name}' is not defined in model family "
                f"'{model_family.name}'. Supported: {supported}"
            )
        validate_single_parameter(param_name, value, family_params[param_name])
