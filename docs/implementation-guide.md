# SP-API Implementation Guide

## Architecture Recommendations

### 1. Module Structure
```
src/zigi_amazon_mcp/
├── server.py              # Main MCP server (keep core functionality)
├── auth.py               # Authentication helpers (extract from server.py)
├── api/
│   ├── __init__.py
│   ├── base.py          # Base API client with common functionality
│   ├── orders.py        # Orders API endpoints
│   ├── inventory.py     # Inventory API endpoints
│   ├── listings.py      # Listings API endpoints
│   ├── feeds.py         # Feeds API endpoints
│   ├── reports.py       # Reports API endpoints
│   └── pricing.py       # Pricing API endpoints
├── utils/
│   ├── __init__.py
│   ├── rate_limiter.py  # Rate limiting implementation
│   ├── cache.py         # Response caching
│   └── validators.py    # Input validation
└── constants.py         # API constants and configurations
```

### 2. Base API Client Pattern

```python
# api/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
from requests_aws4auth import AWS4Auth

class BaseAPIClient(ABC):
    """Base class for all SP-API clients."""
    
    def __init__(self, access_token: str, aws_credentials: Dict[str, str], 
                 region: str = "eu-west-1", endpoint: str = "https://sellingpartnerapi-eu.amazon.com"):
        self.access_token = access_token
        self.aws_auth = AWS4Auth(
            aws_credentials["AccessKeyId"],
            aws_credentials["SecretAccessKey"],
            region,
            "execute-api",
            session_token=aws_credentials["SessionToken"]
        )
        self.endpoint = endpoint
        self.headers = {
            "x-amz-access-token": access_token,
            "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
            "content-type": "application/json"
        }
    
    def _make_request(self, method: str, path: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to SP-API."""
        url = f"{self.endpoint}{path}"
        
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=data,
            headers=self.headers,
            auth=self.aws_auth,
            timeout=30
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=int(response.headers.get("x-amzn-RateLimit-Limit", 60))
            )
        
        response.raise_for_status()
        return response.json()
    
    @abstractmethod
    def get_api_path(self) -> str:
        """Return the base API path for this client."""
        pass
```

### 3. Rate Limiting Implementation

```python
# utils/rate_limiter.py
import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter for SP-API endpoints."""
    
    def __init__(self):
        self.buckets = defaultdict(lambda: {"tokens": 10, "last_update": time.time()})
        self.limits = {
            "/orders/v0/orders": {"rate": 10, "burst": 30},
            "/fba/inventory/v1/summaries": {"rate": 5, "burst": 10},
            "/listings/2021-08-01/items": {"rate": 5, "burst": 10},
            "/feeds/2021-06-30/feeds": {"rate": 15, "burst": 30},
            "/reports/2021-06-30/reports": {"rate": 15, "burst": 30},
            "/products/pricing/v0/price": {"rate": 10, "burst": 20}
        }
        self.lock = Lock()
    
    def check_rate_limit(self, api_path: str) -> bool:
        """Check if request can proceed based on rate limits."""
        with self.lock:
            now = time.time()
            bucket = self.buckets[api_path]
            limit = self.limits.get(api_path, {"rate": 5, "burst": 10})
            
            # Refill tokens based on time passed
            time_passed = now - bucket["last_update"]
            tokens_to_add = time_passed * limit["rate"]
            bucket["tokens"] = min(limit["burst"], bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now
            
            # Check if we have tokens available
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            
            return False
    
    def wait_if_needed(self, api_path: str) -> None:
        """Wait if rate limit is exceeded."""
        while not self.check_rate_limit(api_path):
            time.sleep(0.1)
```

### 4. Caching Layer

```python
# utils/cache.py
from functools import lru_cache, wraps
from datetime import datetime, timedelta
import hashlib
import json

class SPAPICache:
    """Cache for SP-API responses."""
    
    def __init__(self):
        self.cache = {}
        self.ttls = {
            "inventory": timedelta(minutes=5),
            "listings": timedelta(minutes=15),
            "pricing": timedelta(minutes=1),
            "catalog": timedelta(hours=1)
        }
    
    def get_cache_key(self, endpoint: str, params: dict) -> str:
        """Generate cache key from endpoint and parameters."""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Any:
        """Get value from cache if not expired."""
        if key in self.cache:
            value, expiry = self.cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, cache_type: str = "default") -> None:
        """Set value in cache with TTL."""
        ttl = self.ttls.get(cache_type, timedelta(minutes=5))
        expiry = datetime.now() + ttl
        self.cache[key] = (value, expiry)

def cached_api_call(cache_type: str = "default"):
    """Decorator for caching API calls."""
    def decorator(func):
        cache = SPAPICache()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function arguments
            cache_key = cache.get_cache_key(func.__name__, kwargs)
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Make API call
            result = func(*args, **kwargs)
            
            # Cache successful results
            if result and isinstance(result, dict) and result.get("success"):
                cache.set(cache_key, result, cache_type)
            
            return result
        
        return wrapper
    return decorator
```

### 5. Error Handling Strategy

```python
# utils/exceptions.py
class SPAPIError(Exception):
    """Base exception for SP-API errors."""
    pass

class RateLimitError(SPAPIError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after

class AuthenticationError(SPAPIError):
    """Authentication failed."""
    pass

class ValidationError(SPAPIError):
    """Input validation failed."""
    pass

def handle_sp_api_errors(func):
    """Decorator to handle SP-API errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RateLimitError as e:
            return json.dumps({
                "success": False,
                "error": "rate_limit_exceeded",
                "message": str(e),
                "retry_after": e.retry_after
            }, indent=2)
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response else {}
            return json.dumps({
                "success": False,
                "error": "api_error",
                "status_code": e.response.status_code if e.response else None,
                "details": error_data.get("errors", [])
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": "unexpected_error",
                "message": str(e)
            }, indent=2)
    return wrapper
```

### 6. Integration Pattern for MCP Tools

```python
# In server.py, integrate the API clients

from .api.inventory import InventoryAPIClient
from .api.listings import ListingsAPIClient
from .utils.rate_limiter import RateLimiter
from .utils.exceptions import handle_sp_api_errors

# Initialize rate limiter
rate_limiter = RateLimiter()

@mcp.tool()
@handle_sp_api_errors
def get_inventory_summaries(
    auth_token: Annotated[str, "Authentication token"],
    marketplace_ids: Annotated[str, "Comma-separated marketplace IDs"] = "A1F83G8C2ARO7P",
    **kwargs
) -> str:
    """Get FBA inventory summaries."""
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token."
    
    # Rate limit check
    rate_limiter.wait_if_needed("/fba/inventory/v1/summaries")
    
    # Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()
    
    # Use the API client
    client = InventoryAPIClient(access_token, aws_creds)
    result = client.get_inventory_summaries(marketplace_ids, **kwargs)
    
    return json.dumps(result, indent=2)
```

### 7. Testing Strategy

```python
# tests/test_inventory_api.py
import pytest
from unittest.mock import Mock, patch
from zigi_amazon_mcp.api.inventory import InventoryAPIClient

class TestInventoryAPI:
    @pytest.fixture
    def mock_client(self):
        """Create mock inventory client."""
        access_token = "mock_token"
        aws_creds = {
            "AccessKeyId": "mock_key",
            "SecretAccessKey": "mock_secret",
            "SessionToken": "mock_session"
        }
        return InventoryAPIClient(access_token, aws_creds)
    
    @patch('requests.request')
    def test_get_inventory_summaries(self, mock_request, mock_client):
        """Test inventory summaries retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "inventorySummaries": [
                {
                    "asin": "B001234567",
                    "fnSku": "X0001234567",
                    "sellerSku": "MY-SKU-123",
                    "totalQuantity": 100
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = mock_client.get_inventory_summaries("A1F83G8C2ARO7P")
        
        assert result["success"] is True
        assert len(result["inventory"]) == 1
        assert result["inventory"][0]["sellerSku"] == "MY-SKU-123"
```

### 8. Configuration Management

```python
# constants.py
from enum import Enum

class Marketplace(Enum):
    UK = ("A1F83G8C2ARO7P", "https://sellingpartnerapi-eu.amazon.com", "eu-west-1")
    US = ("ATVPDKIKX0DER", "https://sellingpartnerapi-na.amazon.com", "us-east-1")
    DE = ("A1PA6795UKMFR9", "https://sellingpartnerapi-eu.amazon.com", "eu-west-1")
    FR = ("A13V1IB3VIYZZH", "https://sellingpartnerapi-eu.amazon.com", "eu-west-1")
    JP = ("A1VC38T7YXB528", "https://sellingpartnerapi-fe.amazon.com", "us-west-2")
    
    def __init__(self, marketplace_id: str, endpoint: str, region: str):
        self.marketplace_id = marketplace_id
        self.endpoint = endpoint
        self.region = region

class FeedType(Enum):
    INVENTORY_LOADER = "POST_FLAT_FILE_INVLOADER_DATA"
    PRICE_QUANTITY = "POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA"
    LISTINGS = "POST_FLAT_FILE_LISTINGS_DATA"

class ReportType(Enum):
    FBA_INVENTORY = "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"
    MERCHANT_INVENTORY = "GET_MERCHANT_LISTINGS_DATA"
    ACTIVE_LISTINGS = "GET_MERCHANT_LISTINGS_ACTIVE_DATA"
```

## Best Practices Summary

1. **Modular Design**: Separate concerns into distinct modules
2. **Consistent Error Handling**: Use decorators for uniform error responses
3. **Rate Limiting**: Implement proactive rate limiting to avoid 429 errors
4. **Caching**: Cache appropriate responses to reduce API calls
5. **Type Safety**: Use type hints and validation throughout
6. **Testing**: Comprehensive unit and integration tests
7. **Documentation**: Clear docstrings and usage examples
8. **Security**: Never log sensitive data, validate all inputs
9. **Performance**: Use async operations where beneficial
10. **Monitoring**: Log all API interactions for debugging