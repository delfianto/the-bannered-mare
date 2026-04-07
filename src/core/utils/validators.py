"""Validation utilities for identifiers and other fields"""

import re
from re import Pattern

IDENTIFIER_PATTERN: Pattern[str] = re.compile(r"^[a-z][a-z0-9.\-_:/]{0,98}[a-z0-9]$")


def validate_identifier(value: str, field_name: str = "identifier") -> str:
    """
    Validate identifier format.

    Rules:
    - Lowercase only
    - Alphanumeric characters
    - Maximum 100 characters
    - Dash (-), dot (.), underscore (_), colon (:), and slash (/) allowed
    - No spaces allowed
    - Must start and end with alphanumeric

    Args:
        value: The identifier to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        The validated identifier

    Raises:
        ValueError: If identifier doesn't match the pattern
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if not IDENTIFIER_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must be lowercase alphanumeric, "
            f"max 100 chars, special characters allowed: . - _ : / (no spaces): '{value}'"
        )

    return value
