"""Common exceptions for the zigi-amazon-mcp package."""


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after
