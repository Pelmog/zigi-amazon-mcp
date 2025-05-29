"""Base API client for Amazon SP-API interactions."""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from requests_aws4auth import AWS4Auth  # type: ignore[import-untyped]

from ..exceptions import RateLimitError
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BaseAPIClient(ABC):
    """Base class for all SP-API clients."""

    def __init__(
        self,
        access_token: str,
        aws_credentials: Dict[str, str],
        region: str = "eu-west-1",
        endpoint: str = "https://sellingpartnerapi-eu.amazon.com",
    ) -> None:
        """Initialize the base API client.

        Args:
            access_token: Amazon LWA access token
            aws_credentials: AWS credentials dict with AccessKeyId, SecretAccessKey, SessionToken
            region: AWS region for the SP-API endpoint
            endpoint: SP-API endpoint URL
        """
        self.access_token = access_token
        self.region = region
        self.endpoint = endpoint
        
        # Set up AWS4Auth
        self.aws_auth = AWS4Auth(
            aws_credentials["AccessKeyId"],
            aws_credentials["SecretAccessKey"],
            region,
            "execute-api",
            session_token=aws_credentials["SessionToken"],
        )
        
        # Common headers
        self.headers = {
            "x-amz-access-token": access_token,
            "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
            "content-type": "application/json",
        }
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter()

    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (without base URL)
            params: Query parameters
            data: Request body data

        Returns:
            Dict containing the API response

        Raises:
            RateLimitError: When rate limit is exceeded
            requests.HTTPError: For HTTP errors
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.info(f"Request {request_id}: Starting {method} {path}")
        
        # Apply rate limiting
        api_path = self.get_api_path()
        self.rate_limiter.wait_if_needed(api_path)
        
        # Build URL
        url = f"{self.endpoint}{path}"
        
        try:
            # Make request
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=self.headers,
                auth=self.aws_auth,
                timeout=30,
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("x-amzn-RateLimit-Limit", 60))
                logger.warning(f"Request {request_id}: Rate limit exceeded, retry after {retry_after}s")
                raise RateLimitError("Rate limit exceeded", retry_after)
            
            response.raise_for_status()
            result: Dict[str, Any] = response.json()
            
            logger.info(
                f"Request {request_id}: Success in {duration_ms}ms, "
                f"status={response.status_code}"
            )
            
            return result
            
        except requests.HTTPError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(
                f"Request {request_id}: HTTP error in {duration_ms}ms, "
                f"status={e.response.status_code if e.response else 'unknown'}"
            )
            raise
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Request {request_id}: Unexpected error in {duration_ms}ms: {e}")
            raise

    @abstractmethod
    def get_api_path(self) -> str:
        """Return the base API path for this client."""
        pass

    def _format_success_response(
        self, data: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a successful response according to CLAUDE.md standards.

        Args:
            data: The response data
            metadata: Optional metadata to include

        Returns:
            Formatted success response
        """
        response = {
            "success": True,
            "data": data,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            },
        }
        
        if metadata:
            response["metadata"].update(metadata)
            
        return response

    def _format_error_response(
        self,
        error_code: str,
        message: str,
        details: Optional[list] = None,
        retry_after: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Format an error response according to CLAUDE.md standards.

        Args:
            error_code: Standard error code (auth_failed, rate_limit_exceeded, etc.)
            message: Human-readable error message
            details: Optional error details
            retry_after: For rate limit errors, seconds to wait

        Returns:
            Formatted error response
        """
        response = {
            "success": False,
            "error": error_code,
            "message": message,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            },
        }
        
        if details:
            response["details"] = details
        if retry_after:
            response["retry_after"] = retry_after
            
        return response