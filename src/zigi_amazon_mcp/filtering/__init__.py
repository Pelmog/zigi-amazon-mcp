"""
Amazon MCP Server Filtering Module

This module provides comprehensive JSON filtering capabilities with data reduction
and chaining support for Amazon SP-API responses.

Key Components:
- FilterDatabase: Database operations and migrations
- FilterLibrary: High-level filter management
- FilterManager: Filter application and chaining
- Filter types: record, field, chain filters

Usage:
    from zigi_amazon_mcp.filtering import FilterManager

    manager = FilterManager()
    result = manager.apply_filter_by_id(data, "order_summary")
"""

from .database import FilterDatabase, MigrationManager
from .filter_library import FilterChain, FilterDefinition, FilterLibrary, FilterStep
from .filter_manager import FilterManager, FilterResult

__version__ = "1.0.0"
__all__ = [
    "FilterChain",
    "FilterDatabase",
    "FilterDefinition",
    "FilterLibrary",
    "FilterManager",
    "FilterResult",
    "FilterStep",
    "MigrationManager",
]
