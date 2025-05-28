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

1. **get_auth_token** - Generate authentication token (MUST BE CALLED FIRST!)
2. **hello_world** - Simple greeting tool (requires auth_token)
3. **process_text** - Text processing with operations (requires auth_token)
4. **read_file** - Read local file contents (requires auth_token)
5. **write_file** - Write content to local files (requires auth_token)
6. **json_process** - Parse/format JSON data (requires auth_token)
7. **convert_data** - Convert between formats (requires auth_token)
8. **store_session_data** - Store string data by session ID (requires auth_token)
9. **get_session_data** - Retrieve stored session data (requires auth_token)

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
