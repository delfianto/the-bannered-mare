"""Base exceptions for the Bannered Mare application"""

from typing import Any


class BanneredMareException(Exception):
    """Base exception for all application-specific errors.

    ``status_code`` is the HTTP status the global handler maps this to; the
    default is 400 and domain subclasses override it. Business logic raises these
    (never ``HTTPException``) so the service layer stays HTTP-agnostic — the
    handler registered in ``main.py`` does the HTTP translation.
    """

    # int for domain subclasses; ProviderException may leave it None (unknown
    # upstream status) — the handler defaults those to 502.
    status_code: int | None = 400

    def __init__(self, message: str, detail: Any | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(BanneredMareException):
    """A requested resource does not exist (HTTP 404)."""

    status_code = 404


class ConflictError(BanneredMareException):
    """A uniqueness or state conflict, e.g. a duplicate slug (HTTP 409)."""

    status_code = 409


class ValidationError(BanneredMareException):
    """Input that parsed but fails a business rule (HTTP 422)."""

    status_code = 422


class ProviderException(BanneredMareException):
    """Exception raised for errors from AI providers"""

    def __init__(self, message: str, status_code: int | None = None, detail: Any | None = None):
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
