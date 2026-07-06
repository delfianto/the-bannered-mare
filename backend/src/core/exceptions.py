"""Base exceptions for the Candlekeep application"""

from typing import Any


class CandlekeepException(Exception):
    """Base exception for all application-specific errors"""

    def __init__(self, message: str, detail: Any | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class ProviderException(CandlekeepException):
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
