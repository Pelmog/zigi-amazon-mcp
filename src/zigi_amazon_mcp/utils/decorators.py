"""Decorators for SP-API error handling and caching."""

import functools
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable

import requests

from ..exceptions import RateLimitError

logger = logging.getLogger(__name__)


def handle_sp_api_errors(func: Callable[..., str]) -> Callable[..., str]:
    """Decorator to handle SP-API errors consistently.

    This decorator catches common SP-API exceptions and formats them
    according to CLAUDE.md standards.

    Args:
        func: The function to decorate

    Returns:
        Decorated function that handles errors consistently
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        request_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"Request {request_id}: Starting {func.__name__}")
            result = func(*args, **kwargs)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Request {request_id}: Completed {func.__name__} in {duration_ms}ms")

            return result

        except RateLimitError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.warning(f"Request {request_id}: Rate limit exceeded in {duration_ms}ms")

            return json.dumps(
                {
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded. Please wait before making another request.",
                    "retry_after": e.retry_after,
                    "metadata": {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "request_id": request_id,
                    },
                },
                indent=2,
            )

        except requests.HTTPError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            status_code = e.response.status_code if e.response else None
            logger.exception(f"Request {request_id}: HTTP error {status_code} in {duration_ms}ms")

            error_response = {}
            try:
                if e.response:
                    error_response = e.response.json()
            except Exception:
                error_response = {"raw_response": e.response.text if e.response else "No response"}

            # Determine error code based on status
            if status_code == 401:
                error_code = "auth_failed"
                message = "Authentication failed. Check your credentials."
            elif status_code == 403:
                error_code = "auth_failed"
                message = "Access forbidden. Check your IAM role permissions."
            elif status_code == 429:
                error_code = "rate_limit_exceeded"
                message = "Rate limit exceeded."
                retry_after = int(e.response.headers.get("x-amzn-RateLimit-Limit", 60))
            else:
                error_code = "api_error"
                message = "SP-API request failed"

            response = {
                "success": False,
                "error": error_code,
                "message": message,
                "details": error_response.get("errors", []),
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": request_id,
                },
            }

            if status_code == 429:
                response["retry_after"] = retry_after

            return json.dumps(response, indent=2)

        except ValueError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.exception(f"Request {request_id}: Validation error in {duration_ms}ms: {e}")

            return json.dumps(
                {
                    "success": False,
                    "error": "invalid_input",
                    "message": str(e),
                    "metadata": {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "request_id": request_id,
                    },
                },
                indent=2,
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.exception(f"Request {request_id}: Unexpected error in {duration_ms}ms: {e}")

            return json.dumps(
                {
                    "success": False,
                    "error": "unexpected_error",
                    "message": f"An unexpected error occurred: {e!s}",
                    "metadata": {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "request_id": request_id,
                    },
                },
                indent=2,
            )

    return wrapper


def cached_api_call(cache_type: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Decorator for caching API calls (placeholder for future implementation).

    Args:
        cache_type: Type of cache to use (inventory, listings, etc.)

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            # TODO: Implement caching based on cache_type and CACHE_TTLS
            # For now, just pass through to the original function
            return func(*args, **kwargs)

        return wrapper

    return decorator
