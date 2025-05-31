"""Common exceptions for the zigi-amazon-mcp package."""

from typing import Optional


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SPAPIError(Exception):
    """Raised when SP-API returns an error."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class SPAPIRateLimitError(SPAPIError):
    """Raised when SP-API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 120) -> None:
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after
