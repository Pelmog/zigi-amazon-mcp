"""Rate limiting implementation for SP-API endpoints."""

import time
from threading import Lock


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float) -> None:
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Number of tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        with self.lock:
            now = time.time()

            # Add tokens based on time elapsed
            time_passed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            self.last_refill = now

            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until enough tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Time in seconds until tokens are available
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """Rate limiter for SP-API endpoints using token bucket algorithm."""

    # Rate limits by endpoint type (requests per second, burst capacity)
    RATE_LIMITS = {
        "/orders/v0/orders": (10, 30),  # Orders API
        "/fba/inventory/v1/summaries": (5, 10),  # Inventory API
        "/feeds/2021-06-30/feeds": (15, 30),  # Feeds API
        "/reports/2021-06-30/reports": (15, 30),  # Reports API
        "/product-pricing/v0/price": (10, 20),  # Pricing API
        "/listings/2021-08-01/items": (5, 10),  # Listings API for FBM
    }

    def __init__(self) -> None:
        """Initialize rate limiter with token buckets for each endpoint."""
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = Lock()

    def _get_bucket(self, api_path: str) -> TokenBucket:
        """Get or create token bucket for API path.

        Args:
            api_path: The API path to get bucket for

        Returns:
            TokenBucket instance for the API path
        """
        with self.lock:
            if api_path not in self.buckets:
                # Get rate limits for this endpoint
                rate_per_second, burst_capacity = self.RATE_LIMITS.get(
                    api_path,
                    (5, 10),  # Default conservative limits
                )

                self.buckets[api_path] = TokenBucket(capacity=burst_capacity, refill_rate=rate_per_second)

            return self.buckets[api_path]

    def wait_if_needed(self, api_path: str, tokens: int = 1) -> None:
        """Wait if rate limit would be exceeded.

        Args:
            api_path: The API path being accessed
            tokens: Number of tokens to consume (default 1)
        """
        bucket = self._get_bucket(api_path)

        # If tokens aren't available, wait until they are
        if not bucket.consume(tokens):
            wait_time = bucket.time_until_available(tokens)
            if wait_time > 0:
                time.sleep(wait_time)
                # Try again after waiting
                bucket.consume(tokens)

    def check_available(self, api_path: str, tokens: int = 1) -> bool:
        """Check if tokens are available without consuming them.

        Args:
            api_path: The API path being checked
            tokens: Number of tokens needed

        Returns:
            True if tokens are available
        """
        bucket = self._get_bucket(api_path)
        return bucket.tokens >= tokens

    def get_wait_time(self, api_path: str, tokens: int = 1) -> float:
        """Get time to wait until tokens are available.

        Args:
            api_path: The API path being checked
            tokens: Number of tokens needed

        Returns:
            Time in seconds to wait
        """
        bucket = self._get_bucket(api_path)
        return bucket.time_until_available(tokens)
