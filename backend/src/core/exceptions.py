"""Base exceptions for the Bannered Mare application"""

from typing import Any


class BanneredMareException(Exception):
    """Base exception for all application-specific errors.

    ``status_code`` is the HTTP status the global handler maps this to; the
    default is 400 and domain subclasses override it. Business logic raises these
    (never ``HTTPException``) so the service layer stays HTTP-agnostic — the
    handler registered in ``main.py`` does the HTTP translation.
    """

    # Each domain subclass declares the HTTP status the handler maps it to.
    status_code: int | None = 400

    def __init__(self, message: str, detail: Any | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class BadRequestError(BanneredMareException):
    """A malformed or inapplicable request (HTTP 400)."""

    status_code = 400


class NotFoundError(BanneredMareException):
    """A requested resource does not exist (HTTP 404)."""

    status_code = 404


class ConflictError(BanneredMareException):
    """A uniqueness or state conflict, e.g. a duplicate slug (HTTP 409)."""

    status_code = 409


class ValidationError(BanneredMareException):
    """Input that parsed but fails a business rule (HTTP 422)."""

    status_code = 422


class PayloadTooLargeError(BanneredMareException):
    """An upload exceeds the allowed size (HTTP 413)."""

    status_code = 413


class ProviderException(BanneredMareException):
    """Error from an upstream AI provider (HTTP 502 by default).

    ``status_code`` may be overridden to pass an upstream status through (e.g. a
    401/429 from the provider); left at the default it maps to 502 Bad Gateway.
    """

    def __init__(self, message: str, status_code: int | None = 502, detail: Any | None = None):
        super().__init__(message, detail)
        self.status_code = status_code


class ProviderAuthError(ProviderException):
    """Raised when authentication with provider fails"""

    pass


class ProviderTimeoutError(ProviderException):
    """Raised when provider request times out"""

    pass


class ProviderRateLimitError(ProviderException):
    """Raised when provider rate limit is hit"""

    pass


class ProviderInvalidRequestError(ProviderException):
    """Raised when request payload is invalid"""

    pass
