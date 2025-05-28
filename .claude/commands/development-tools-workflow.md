# Development Tools Workflow for Zigi Amazon MCP

## Overview
This document outlines the development tools and workflows for building MCP (Model Context Protocol) servers using Flask, Python 3.12, and UV package management.

## 1. Development Stack

### 1.1 Core Technologies
- **Python**: 3.12 (preferred version)
- **Package Manager**: UV (modern Python package manager)
- **Web Framework**: Flask (for API endpoints)
- **MCP SDK**: Model Context Protocol SDK for server implementation
- **Testing**: pytest with coverage
- **Type Checking**: mypy with strict mode
- **Linting**: ruff for code quality

### 1.2 Python Version Management
```bash
# Check current Python version
python --version

# Ensure Python 3.12 is being used
# UV will respect .python-version file or pyproject.toml constraints
echo "3.12" > .python-version

# UV automatically manages Python versions
uv python pin 3.12
```

## 2. UV Package Management

### 2.1 Initial Setup
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via homebrew on macOS
brew install uv

# Initialize UV in project (if not already done)
uv init
```

### 2.2 Dependency Management
```bash
# Add production dependencies
uv add flask
uv add mcp
uv add boto3  # For Amazon API integration
uv add pydantic  # For data validation

# Add development dependencies
uv add --dev pytest pytest-cov pytest-asyncio
uv add --dev mypy types-flask types-requests
uv add --dev ruff
uv add --dev ipython

# Install all dependencies
uv sync

# Update dependencies
uv lock --upgrade-package <package-name>
uv sync
```

### 2.3 Virtual Environment
```bash
# UV automatically manages virtual environments
# Activate the environment (UV handles this automatically)
uv run <command>

# Or activate manually
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

# Run commands in UV environment
uv run python script.py
uv run pytest
uv run flask run
```

## 3. MCP Server Development

### 3.1 MCP Server Structure
```
src/zigi_amazon_mcp/
├── __init__.py
├── server.py          # Main MCP server implementation
├── handlers/          # Request handlers
│   ├── __init__.py
│   ├── products.py    # Product-related handlers
│   ├── orders.py      # Order-related handlers
│   └── inventory.py   # Inventory handlers
├── tools/             # MCP tools implementation
│   ├── __init__.py
│   └── amazon_tools.py
├── api/               # Flask API endpoints
│   ├── __init__.py
│   ├── app.py        # Flask application
│   └── routes.py     # API routes
└── utils/             # Utility functions
    ├── __init__.py
    ├── auth.py       # Amazon API authentication
    └── rate_limit.py # Rate limiting
```

### 3.2 Basic MCP Server Template
```python
# src/zigi_amazon_mcp/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncio

# Create server instance
server = Server("zigi-amazon-mcp")

@server.list_tools()
async def list_tools():
    """List available MCP tools"""
    return [
        {
            "name": "search_products",
            "description": "Search Amazon products",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool"""
    if name == "search_products":
        # Implement product search logic
        pass

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 Flask Integration
```python
# src/zigi_amazon_mcp/api/app.py
from flask import Flask, jsonify, request
from ..handlers import products

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.DevelopmentConfig')
    
    # Register blueprints
    app.register_blueprint(products.bp, url_prefix='/api/products')
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"})
    
    return app

# Run Flask app
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
```

## 4. Development Workflow

### 4.1 Setting Up New MCP Server
```bash
# Create new MCP server module
mkdir -p src/zigi_amazon_mcp/servers/<server-name>
touch src/zigi_amazon_mcp/servers/<server-name>/__init__.py
touch src/zigi_amazon_mcp/servers/<server-name>/server.py

# Add MCP configuration
cat > mcp.json << 'EOF'
{
  "mcpServers": {
    "zigi-amazon": {
      "command": "uv",
      "args": ["run", "python", "-m", "zigi_amazon_mcp.server"],
      "env": {
        "AMAZON_ACCESS_KEY": "${AMAZON_ACCESS_KEY}",
        "AMAZON_SECRET_KEY": "${AMAZON_SECRET_KEY}"
      }
    }
  }
}
EOF
```

### 4.2 Running Services
```bash
# Run MCP server
uv run python -m zigi_amazon_mcp.server

# Run Flask development server
uv run flask --app src/zigi_amazon_mcp/api/app run --debug

# Or use make commands
make run-mcp
make run-api

# Run both with process manager
uv run honcho start
```

### 4.3 Testing MCP Tools
```python
# tests/test_mcp_tools.py
import pytest
from zigi_amazon_mcp.server import server

@pytest.mark.asyncio
async def test_search_products_tool():
    """Test the search_products MCP tool"""
    result = await server.call_tool(
        "search_products",
        {"query": "laptop", "category": "Electronics"}
    )
    assert result is not None
    assert "products" in result
```

## 5. Best Practices

### 5.1 MCP Server Guidelines
1. **Tool Naming**: Use descriptive, action-based names (e.g., `search_products`, not `products`)
2. **Error Handling**: Always return proper error responses with helpful messages
3. **Rate Limiting**: Implement rate limiting for Amazon API calls
4. **Caching**: Cache frequently accessed data to reduce API calls
5. **Logging**: Use structured logging for debugging

### 5.2 Flask API Guidelines
1. **RESTful Design**: Follow REST principles for API endpoints
2. **Validation**: Use Pydantic for request/response validation
3. **Authentication**: Implement proper API key authentication
4. **CORS**: Configure CORS appropriately for client access
5. **Documentation**: Use Flask-RESTX or similar for API documentation

### 5.3 UV/Python Guidelines
1. **Lock Files**: Always commit `uv.lock` for reproducible builds
2. **Python Version**: Pin Python version in `pyproject.toml`
3. **Type Hints**: Use type hints throughout the codebase
4. **Async/Await**: Use async patterns for MCP server operations
5. **Dependencies**: Keep dependencies minimal and up-to-date

## 6. Common Commands Reference

```bash
# Environment setup
uv sync                        # Install all dependencies
uv add <package>              # Add new dependency
uv remove <package>           # Remove dependency
uv run <command>              # Run command in virtual env

# Development
uv run python -m zigi_amazon_mcp.server  # Run MCP server
uv run flask run              # Run Flask app
uv run pytest                 # Run tests
uv run mypy src              # Type checking
uv run ruff check .          # Lint code
uv run ruff format .         # Format code

# MCP specific
uv run mcp-inspector         # Test MCP server interface
uv run python -m zigi_amazon_mcp.tools --list  # List available tools

# Project management
make install                  # Full environment setup
make test                    # Run all tests
make check                   # Run all checks
make build                   # Build distribution
```

## 7. Troubleshooting

### 7.1 Common Issues
1. **Python Version Mismatch**
   ```bash
   # Ensure UV uses correct Python
   uv python pin 3.12
   uv sync --refresh
   ```

2. **MCP Server Not Starting**
   ```bash
   # Check logs
   uv run python -m zigi_amazon_mcp.server --debug
   
   # Verify MCP tools
   uv run python -c "from zigi_amazon_mcp.server import server; print(server.list_tools())"
   ```

3. **Flask App Issues**
   ```bash
   # Run with debug info
   FLASK_ENV=development uv run flask run --debug
   
   # Check port availability
   lsof -i :5000
   ```

### 7.2 Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# MCP server debug mode
server = Server("zigi-amazon-mcp", debug=True)

# Flask debug mode
app.run(debug=True)
```

## 8. Integration with Git Workflow

When developing MCP servers or Flask APIs:

1. Create feature branch following Git workflow
2. Set up UV environment with `uv sync`
3. Implement MCP tools/Flask endpoints
4. Write tests for new functionality
5. Run `make check` before committing
6. Create PR and request Claude review

Remember: Always use UV for package management and maintain Python 3.12 compatibility throughout development.