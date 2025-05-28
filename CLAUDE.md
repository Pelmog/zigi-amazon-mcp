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