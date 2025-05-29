# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
make install                    # Install environment and pre-commit hooks
uv run pre-commit run -a       # Run all pre-commit hooks
```

### Testing and Quality Checks
```bash
make test                      # Run pytest with coverage
uv run python -m pytest       # Run tests without coverage
make check                     # Run all quality checks (pre-commit, mypy, deptry)
uv run mypy                    # Type checking
uv run deptry src              # Check for obsolete dependencies
```

### Building and Publishing
```bash
make build                     # Build wheel file
make docs                      # Build and serve documentation
make docs-test                 # Test documentation build
```

## Project Architecture

This is an MCP (Model Context Protocol) server for connecting to the Amazon Seller Central API. The project follows a standard Python package structure:

- **Source code**: `src/zigi_amazon_mcp/` - Main package directory
- **Tests**: `tests/` - Test files using pytest
- **Documentation**: `docs/` - MkDocs documentation
- **Configuration**: Uses `pyproject.toml` for project configuration, dependencies, and tool settings

### Development Tools
- **Package manager**: `uv` for dependency management and virtual environments
- **Linting**: `ruff` for code formatting and linting
- **Type checking**: `mypy` with strict configuration
- **Testing**: `pytest` with coverage reporting
- **Documentation**: `MkDocs` with Material theme
- **CI/CD**: GitHub Actions for testing across Python 3.9-3.13

### Key Configuration
- Python compatibility: 3.9-3.13
- Line length: 120 characters (ruff)
- Test coverage reporting enabled
- Pre-commit hooks for code quality

## MCP Server Implementation Details

### FastMCP Framework
The server uses FastMCP for MCP protocol implementation. Key details:
- Server instance: `mcp = FastMCP("zigi-amazon-mcp")`
- Tools are defined using the `@mcp.tool()` decorator
- Type hints with `Annotated` are used for parameter descriptions
- Entry point is `mcp.run()` in the `main()` function

### Available MCP Tools/Endpoints

**AUTHENTICATION REQUIRED**: All functions (except get_auth_token) now require authentication!

#### Core Utility Tools
1. **get_auth_token** - Generate authentication token (MUST BE CALLED FIRST!)
2. **hello_world** - Simple greeting tool (requires auth_token)
3. **process_text** - Text processing with operations (requires auth_token)
4. **read_file** - Read local file contents (requires auth_token)
5. **write_file** - Write content to local files (requires auth_token)
6. **json_process** - Parse/format JSON data (requires auth_token)
7. **convert_data** - Convert between formats (requires auth_token)
8. **store_session_data** - Store string data by session ID (requires auth_token)
9. **get_session_data** - Retrieve stored session data (requires auth_token)

#### Amazon SP-API Tools
10. **get_orders** - Retrieve Amazon orders with pagination (requires auth_token + env vars)
11. **get_order** - Retrieve single Amazon order details (requires auth_token + env vars)

### Session Storage Implementation

**IMPORTANT**: The current session storage uses an in-memory dictionary:
```python
session_store: dict[str, str] = {}
```

**Limitations and Considerations**:
- Data is NOT persistent - lost when server restarts
- No session expiration or TTL
- No size limits or memory management
- No authentication or session validation
- Only supports string data (no complex objects)
- Thread-safety not implemented (could be issue with concurrent requests)

**Future Improvements Needed**:
- Use proper session store (Redis, database, etc.) for production
- Add session expiration/TTL
- Implement size limits to prevent memory issues
- Add authentication/validation for session access
- Support for storing complex data types (JSON serialization)
- Add thread-safety with locks if needed

### Testing MCP Endpoints

When testing MCP endpoints:
1. Use the `mcp__zigi-amazon-mcp__<tool_name>` format for tool invocation
2. Check `mcp` command output to ensure server is connected
3. Test edge cases (empty inputs, special characters, large data)
4. Verify error handling and appropriate error messages
5. Document test results in `logs/` directory with timestamp

### Common Issues and Solutions

1. **MCP Server Not Connecting**:
   - Check if server is running with `mcp` command
   - Verify server.py has no syntax errors
   - Ensure FastMCP is properly installed

2. **Type Checking Errors**:
   - Use `Annotated[type, "description"]` for all tool parameters
   - Ensure return types are specified for all functions
   - Run `uv run mypy` to catch type issues early

3. **Session Data Lost**:
   - Remember: session storage is in-memory only
   - Data persists only during server lifetime
   - Plan for proper persistence before production use

## Authentication System

### How Authentication Works

**CRITICAL**: All MCP functions (except get_auth_token) now require authentication!

1. **First Step - Get Auth Token**:
   ```
   Call: mcp__zigi-amazon-mcp__get_auth_token()
   Returns: "Authentication successful. Your auth token is: <64-character-hex-token>"
   ```

2. **Use Token in All Subsequent Calls**:
   ```
   Call: mcp__zigi-amazon-mcp__hello_world(auth_token="<token>", name="World")
   ```

### Authentication Implementation Details

- **Token Generation**: Uses `secrets.token_hex(32)` for cryptographically secure tokens
- **Token Storage**: Stored in memory using a set: `auth_tokens: set[str]`
- **Validation**: Simple membership check in the auth_tokens set
- **Error Message**: Consistent error for all functions when auth fails

### Important Authentication Notes

1. **AI Agent Usage**:
   - MUST call get_auth_token() before any other function
   - Store the token and reuse it for all calls in the session
   - If you get "Invalid or missing auth token" error, get a new token

2. **Current Limitations**:
   - Tokens never expire (only valid for server lifetime)
   - No token revocation mechanism
   - No rate limiting or usage tracking per token
   - No association between auth tokens and session data

3. **Session ID vs Auth Token**:
   - Auth Token: Required for authentication (from get_auth_token)
   - Session ID: Used for organizing data storage (any string you choose)
   - They are completely separate concepts

4. **Production Improvements Needed**:
   - Token expiration with TTL
   - Token refresh mechanism
   - Rate limiting per token
   - Association of session data with auth tokens
   - Secure token storage (database/cache)
   - Token revocation capabilities

## Amazon SP-API Implementation Standards

### Module Organization

When implementing new SP-API endpoints, follow this structure:

```
src/zigi_amazon_mcp/
├── server.py              # Main MCP server - keep only MCP tool decorators
├── auth.py               # Extract authentication helpers here
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
└── constants.py         # API constants and marketplace configurations
```

### Base API Client Pattern

All SP-API implementations MUST inherit from a base client:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAPIClient(ABC):
    """Base class for all SP-API clients."""
    
    def __init__(self, access_token: str, aws_credentials: Dict[str, str], 
                 region: str = "eu-west-1", 
                 endpoint: str = "https://sellingpartnerapi-eu.amazon.com"):
        # Initialize AWS4Auth, headers, etc.
        pass
    
    def _make_request(self, method: str, path: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request with rate limiting and error handling."""
        pass
    
    @abstractmethod
    def get_api_path(self) -> str:
        """Return the base API path for this client."""
        pass
```

### MCP Tool Implementation Pattern

When adding new SP-API endpoints as MCP tools:

```python
@mcp.tool()
@handle_sp_api_errors  # Always use error handling decorator
@cached_api_call(cache_type="inventory")  # Use caching where appropriate
def get_inventory_summaries(
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token()"],
    marketplace_ids: Annotated[str, "Comma-separated marketplace IDs"] = "A1F83G8C2ARO7P",
    # Include all API parameters with clear descriptions
    **kwargs  # Allow additional parameters for flexibility
) -> str:
    """Clear description of what this endpoint does.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token.
    
    Document the main use cases and any important limitations.
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token."
    
    # 2. Apply rate limiting
    rate_limiter.wait_if_needed(api_path)
    
    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()
    
    # 4. Use appropriate API client
    client = InventoryAPIClient(access_token, aws_creds)
    
    # 5. Make API call
    result = client.method_name(marketplace_ids, **kwargs)
    
    # 6. Return formatted JSON
    return json.dumps(result, indent=2)
```

### Rate Limiting Requirements

**CRITICAL**: All SP-API endpoints MUST implement rate limiting:

1. **Token Bucket Algorithm**: Use the provided RateLimiter class
2. **Endpoint-Specific Limits**: Configure per-endpoint rate limits
3. **429 Error Handling**: Implement exponential backoff
4. **Proactive Limiting**: Check limits BEFORE making requests

Rate limits by endpoint type:
- Orders API: 10 requests/second, burst of 30
- Inventory API: 5 requests/second, burst of 10
- Feeds API: 15 requests/second, burst of 30
- Reports API: 15 requests/second, burst of 30
- Pricing API: 10 requests/second, burst of 20

### Error Handling Standards

All SP-API functions MUST return consistent JSON error responses:

```python
# Success response
{
    "success": true,
    "data": { ... },
    "metadata": {
        "timestamp": "2025-01-29T10:30:00Z",
        "marketplace": "UK",
        "request_id": "abc-123"
    }
}

# Error response
{
    "success": false,
    "error": "rate_limit_exceeded",  # Use consistent error codes
    "message": "Human-readable error message",
    "details": [...],  # Include SP-API error details if available
    "retry_after": 60  # For rate limit errors
}
```

Error codes to use:
- `auth_failed`: Authentication issues
- `rate_limit_exceeded`: 429 errors
- `invalid_input`: Validation failures
- `api_error`: SP-API returned an error
- `network_error`: Connection issues
- `unexpected_error`: Unhandled exceptions

### Caching Strategy

Implement caching for appropriate endpoints:

```python
# Cache TTLs by data type
CACHE_TTLS = {
    "inventory": timedelta(minutes=5),      # Changes frequently
    "listings": timedelta(minutes=15),      # More stable
    "pricing": timedelta(minutes=1),        # Very dynamic
    "catalog": timedelta(hours=1),          # Rarely changes
    "orders": None,                         # Never cache orders
}
```

### Input Validation

All parameters MUST be validated before API calls:

```python
# validators.py
def validate_marketplace_id(marketplace_id: str) -> bool:
    """Validate marketplace ID format and existence."""
    return marketplace_id in VALID_MARKETPLACE_IDS

def validate_iso8601_date(date_string: str) -> bool:
    """Validate ISO 8601 date format."""
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except:
        return False

def validate_seller_sku(sku: str) -> bool:
    """Validate seller SKU format."""
    # SKUs must not contain certain special characters
    forbidden_chars = ['<', '>', ':', '"', '|', '?', '*']
    return not any(char in sku for char in forbidden_chars)
```

### Pagination Handling

For endpoints that return paginated results:

```python
def handle_pagination(client, method, params, max_results=1000):
    """Generic pagination handler for SP-API endpoints."""
    all_results = []
    next_token = None
    
    while len(all_results) < max_results:
        if next_token:
            params['nextToken'] = next_token
        
        response = client.make_request(method, params)
        results = response.get('data', [])
        
        # Add results up to max_results
        remaining = max_results - len(all_results)
        all_results.extend(results[:remaining])
        
        # Check for more pages
        next_token = response.get('nextToken')
        if not next_token or len(all_results) >= max_results:
            break
    
    return all_results
```

### Marketplace Configuration

Use the centralized marketplace configuration:

```python
# constants.py
MARKETPLACES = {
    "UK": {
        "id": "A1F83G8C2ARO7P",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "GBP"
    },
    "US": {
        "id": "ATVPDKIKX0DER",
        "endpoint": "https://sellingpartnerapi-na.amazon.com",
        "region": "us-east-1",
        "currency": "USD"
    },
    # Add all supported marketplaces
}
```

### Testing Requirements

All new SP-API endpoints MUST include:

1. **Unit Tests**: Mock API responses
2. **Integration Tests**: Use sandbox environment
3. **Error Case Tests**: Test all error scenarios
4. **Rate Limit Tests**: Verify rate limiting works

Example test structure:
```python
class TestInventoryAPI:
    def test_get_inventory_success(self, mock_client):
        """Test successful inventory retrieval."""
        pass
    
    def test_get_inventory_rate_limit(self, mock_client):
        """Test rate limit handling."""
        pass
    
    def test_get_inventory_auth_error(self, mock_client):
        """Test authentication error handling."""
        pass
```

### Documentation Standards

Each new endpoint MUST include:

1. **Docstring**: Clear description, parameters, return format
2. **Usage Example**: Show common use case
3. **Error Examples**: Document possible errors
4. **Rate Limits**: Specify endpoint limits
5. **Required Scopes**: List SP-API permissions needed

### Security Considerations

1. **Never Log Sensitive Data**: No tokens, addresses, or PII in logs
2. **Validate All Inputs**: Prevent injection attacks
3. **Use Environment Variables**: For all credentials
4. **Implement Request Signing**: Use AWS4Auth for all requests
5. **HTTPS Only**: Never allow HTTP connections

### Performance Guidelines

1. **Batch Operations**: Use Feeds API for >10 items
2. **Concurrent Requests**: Use asyncio for parallel operations
3. **Connection Pooling**: Reuse HTTP connections
4. **Response Streaming**: For large report downloads
5. **Circuit Breakers**: Prevent cascading failures

### Monitoring and Logging

Implement comprehensive logging:

```python
import logging

logger = logging.getLogger(__name__)

# Log format
LOG_FORMAT = {
    "timestamp": "ISO8601",
    "level": "INFO|WARNING|ERROR",
    "endpoint": "API endpoint path",
    "marketplace": "Marketplace ID",
    "duration_ms": "Request duration",
    "status_code": "HTTP status",
    "error_code": "SP-API error code if any",
    "request_id": "Unique request identifier"
}
```

### Environment Variables

Required for SP-API:
```bash
# Login with Amazon (LWA)
LWA_CLIENT_ID=your_client_id
LWA_CLIENT_SECRET=your_client_secret
LWA_REFRESH_TOKEN=your_refresh_token

# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_ROLE_ARN=arn:aws:iam::account:role/role-name  # Optional

# Optional Configuration
SP_API_SANDBOX=false  # Use sandbox environment
SP_API_TIMEOUT=30     # Request timeout in seconds
SP_API_RETRY_COUNT=3  # Number of retries
```

### Common Pitfalls to Avoid

1. **Don't Cache Orders**: Order data should always be fresh
2. **Don't Ignore Rate Limits**: Always implement rate limiting
3. **Don't Use Sync for Bulk**: Use async for large operations
4. **Don't Parse HTML**: Use proper API endpoints only
5. **Don't Store Credentials**: Use environment variables

### SP-API Endpoint Priority

When implementing new endpoints, follow this priority:

1. **Inventory Management** (Phase 1)
   - FBA Inventory Summaries
   - Listings API for updates
   - Inventory Health metrics

2. **Bulk Operations** (Phase 2)
   - Feeds API
   - Reports API

3. **Fulfillment** (Phase 3)
   - FBA Inbound
   - FBA Outbound

4. **Pricing & Competition** (Phase 4)
   - Product Pricing
   - Competitive Analysis

5. **Catalog** (Phase 5)
   - Product Search
   - Catalog Details

### Code Generation Best Practices

When implementing new SP-API functionality:

1. **File Creation Guidelines**:
   - Create new module files in `api/` directory for each SP-API domain
   - Create utility files in `utils/` only for reusable components
   - Never duplicate functionality - extract common patterns to base classes

2. **Import Organization**:
   ```python
   # Standard library imports
   import json
   from datetime import datetime, timedelta
   from typing import Dict, Any, Optional
   
   # Third-party imports
   import requests
   from requests_aws4auth import AWS4Auth  # type: ignore[import-untyped]
   
   # Local imports
   from .base import BaseAPIClient
   from ..utils.rate_limiter import RateLimiter
   from ..utils.validators import validate_marketplace_id
   ```

3. **Type Annotations**:
   - Use `Annotated[type, "description"]` for all MCP tool parameters
   - Use proper return type hints for all functions
   - Add `# type: ignore[import-untyped]` for libraries without stubs

4. **Error Handling Pattern**:
   ```python
   try:
       # API call logic
       response = self._make_request(...)
       return {"success": True, "data": response}
   except RateLimitError as e:
       return {"success": False, "error": "rate_limit_exceeded", "retry_after": e.retry_after}
   except requests.HTTPError as e:
       return {"success": False, "error": "api_error", "details": e.response.json()}
   except Exception as e:
       logger.error(f"Unexpected error: {e}")
       return {"success": False, "error": "unexpected_error", "message": str(e)}
   ```

5. **Docstring Format**:
   ```python
   def function_name(param: str) -> Dict[str, Any]:
       """One-line summary of function purpose.
       
       Detailed description of what the function does, when to use it,
       and any important considerations.
       
       Args:
           param: Description of the parameter
           
       Returns:
           Description of return value structure
           
       Raises:
           RateLimitError: When rate limit is exceeded
           ValidationError: When input validation fails
           
       Example:
           >>> result = function_name("value")
           >>> print(result["success"])
           True
       """
   ```

6. **Constant Definitions**:
   - Define API paths in class constants
   - Define rate limits in module constants
   - Use enums for fixed value sets

7. **Testing Patterns**:
   ```python
   @pytest.fixture
   def mock_api_client():
       """Create mock API client with test credentials."""
       return APIClient("test_token", {"AccessKeyId": "test"})
   
   @patch('requests.request')
   def test_api_call(mock_request, mock_api_client):
       """Test pattern for API calls."""
       # Setup mock response
       mock_response = Mock()
       mock_response.status_code = 200
       mock_response.json.return_value = {"test": "data"}
       mock_request.return_value = mock_response
       
       # Make call
       result = mock_api_client.method()
       
       # Assertions
       assert result["success"] is True
       mock_request.assert_called_once()
   ```

### Implementation Checklist

For each new SP-API endpoint, ensure:

- [ ] Authentication validation is first check
- [ ] Rate limiting is applied before API call
- [ ] Input validation uses validators.py functions
- [ ] Error handling follows standard pattern
- [ ] Response format matches success/error structure
- [ ] Caching is implemented where appropriate
- [ ] Unit tests cover success and error cases
- [ ] Documentation includes usage examples
- [ ] Type hints are complete and accurate
- [ ] Logging captures key metrics

### Code Review Standards

Before marking any SP-API implementation as complete:

1. **Functionality**:
   - Endpoint works with real API
   - Handles all documented parameters
   - Pagination works correctly
   - Rate limiting prevents 429 errors

2. **Code Quality**:
   - Follows module structure
   - No code duplication
   - Clear variable names
   - Appropriate comments

3. **Error Handling**:
   - All exceptions caught
   - Meaningful error messages
   - Consistent error format
   - Retry logic for transient errors

4. **Security**:
   - No hardcoded credentials
   - Input validation prevents injection
   - Sensitive data not logged
   - HTTPS enforced

5. **Performance**:
   - Caching implemented
   - Batch operations supported
   - Connection reuse
   - Reasonable timeouts

6. **Documentation**:
   - Complete docstrings
   - Usage examples
   - Error scenarios documented
   - Rate limits specified

### SP-API Response Data Handling

When processing SP-API responses:

1. **Extract Nested Data Safely**:
   ```python
   # Good: Safe nested access
   orders = result.get("payload", {}).get("Orders", [])
   
   # Bad: Can raise KeyError
   orders = result["payload"]["Orders"]
   ```

2. **Transform API Data**:
   ```python
   # Transform raw API response to consistent format
   def transform_inventory_item(api_item: Dict) -> Dict:
       return {
           "sku": api_item.get("sellerSku"),
           "asin": api_item.get("asin"),
           "quantity": {
               "total": api_item.get("totalQuantity", 0),
               "available": api_item.get("inventoryDetails", {}).get("fulfillableQuantity", 0),
               "reserved": api_item.get("inventoryDetails", {}).get("reservedQuantity", {}).get("totalReservedQuantity", 0)
           },
           "last_updated": api_item.get("lastUpdatedTime")
       }
   ```

3. **Handle Missing Fields**:
   - Use `.get()` with defaults for optional fields
   - Document which fields are guaranteed vs optional
   - Validate required fields before processing

### Async Implementation Guidelines

For bulk operations or multiple API calls:

1. **Use asyncio for Parallel Requests**:
   ```python
   import asyncio
   import aiohttp
   
   async def fetch_multiple_items(skus: List[str]) -> List[Dict]:
       async with aiohttp.ClientSession() as session:
           tasks = [fetch_item(session, sku) for sku in skus]
           return await asyncio.gather(*tasks)
   ```

2. **Implement Semaphore for Rate Limiting**:
   ```python
   # Limit concurrent requests
   semaphore = asyncio.Semaphore(5)
   
   async def fetch_with_limit(session, url):
       async with semaphore:
           return await fetch(session, url)
   ```

3. **Batch Processing Pattern**:
   ```python
   def process_in_batches(items: List[Any], batch_size: int = 50):
       for i in range(0, len(items), batch_size):
           batch = items[i:i + batch_size]
           yield batch
   ```

### Debugging and Troubleshooting

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Log API requests/responses (sanitize sensitive data)
   logger.debug(f"API Request: {method} {path}")
   logger.debug(f"API Response: {response.status_code}")
   ```

2. **Common Issues**:
   - **401 Unauthorized**: Check LWA token refresh
   - **403 Forbidden**: Verify IAM role permissions
   - **429 Too Many Requests**: Implement backoff
   - **500 Server Error**: Retry with exponential backoff

3. **Request ID Tracking**:
   ```python
   import uuid
   
   request_id = str(uuid.uuid4())
   logger.info(f"Request {request_id}: Starting API call")
   # Include request_id in all related log messages
   ```

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
