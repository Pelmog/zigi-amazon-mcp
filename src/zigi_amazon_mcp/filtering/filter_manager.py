"""
Filter manager for applying filters and chains to data.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .filter_library import FilterDefinition, FilterLibrary

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of filter application."""

    success: bool
    data: Any
    original_size_bytes: int
    final_size_bytes: int
    reduction_percent: float
    execution_time_ms: float
    filters_applied: list[str]
    error: Optional[str] = None
    metadata: dict[str, Any] = None


class FilterManager:
    """Manages filter application and chaining operations."""

    def __init__(self, db_path: Optional[str] = None):
        self.filter_library = FilterLibrary(db_path)

    def apply_filter_by_id(self, data: Any, filter_id: str, params: Optional[dict[str, Any]] = None) -> FilterResult:
        """Apply a single filter by ID."""
        start_time = time.time()
        original_size = len(json.dumps(data, default=str))

        try:
            filter_def = self.filter_library.get_filter_by_id(filter_id)
            if not filter_def:
                return FilterResult(
                    success=False,
                    data=data,
                    original_size_bytes=original_size,
                    final_size_bytes=original_size,
                    reduction_percent=0.0,
                    execution_time_ms=0.0,
                    filters_applied=[],
                    error=f"Filter '{filter_id}' not found",
                )

            if filter_def.filter_type == "chain":
                return self.apply_filter_chain(data, filter_id, params)
            else:
                result = self._apply_single_filter(data, filter_def, params or {})

            final_size = len(json.dumps(result, default=str))
            reduction_percent = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0.0
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=True,
                data=result,
                original_size_bytes=original_size,
                final_size_bytes=final_size,
                reduction_percent=reduction_percent,
                execution_time_ms=execution_time,
                filters_applied=[filter_id],
            )

        except Exception as e:
            logger.exception(f"Error applying filter {filter_id}: {e}")
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=False,
                data=data,
                original_size_bytes=original_size,
                final_size_bytes=original_size,
                reduction_percent=0.0,
                execution_time_ms=execution_time,
                filters_applied=[],
                error=str(e),
            )

    def apply_filter_chain(self, data: Any, chain_filter_id: str, params: Optional[dict[str, Any]] = None) -> FilterResult:
        """Apply a predefined filter chain."""
        start_time = time.time()
        original_size = len(json.dumps(data, default=str))
        applied_filters = []

        try:
            chain = self.filter_library.get_filter_chain(chain_filter_id)
            if not chain:
                return FilterResult(
                    success=False,
                    data=data,
                    original_size_bytes=original_size,
                    final_size_bytes=original_size,
                    reduction_percent=0.0,
                    execution_time_ms=0.0,
                    filters_applied=[],
                    error=f"Filter chain '{chain_filter_id}' not found",
                )

            result = data
            step_results = []

            for step in chain.steps:
                if not step.filter_def:
                    raise ValueError(f"Step filter '{step.filter_id}' not found in chain")

                step_start_size = len(json.dumps(result, default=str))
                result = self._apply_single_filter(result, step.filter_def, params or {})
                step_end_size = len(json.dumps(result, default=str))

                step_reduction = (
                    ((step_start_size - step_end_size) / step_start_size * 100) if step_start_size > 0 else 0.0
                )

                step_results.append({
                    "step_order": step.order,
                    "filter_id": step.filter_id,
                    "size_before": step_start_size,
                    "size_after": step_end_size,
                    "reduction_percent": step_reduction,
                })

                applied_filters.append(step.filter_id)
                logger.debug(f"Chain step {step.order} ({step.filter_id}): {step_reduction:.1f}% reduction")

            final_size = len(json.dumps(result, default=str))
            total_reduction = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0.0
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=True,
                data=result,
                original_size_bytes=original_size,
                final_size_bytes=final_size,
                reduction_percent=total_reduction,
                execution_time_ms=execution_time,
                filters_applied=applied_filters,
                metadata={
                    "chain_id": chain_filter_id,
                    "chain_name": chain.name,
                    "step_results": step_results,
                    "expected_reduction": chain.estimated_reduction,
                },
            )

        except Exception as e:
            logger.exception(f"Error applying filter chain {chain_filter_id}: {e}")
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=False,
                data=data,
                original_size_bytes=original_size,
                final_size_bytes=original_size,
                reduction_percent=0.0,
                execution_time_ms=execution_time,
                filters_applied=applied_filters,
                error=str(e),
            )

    def apply_custom_chain(self, data: Any, filter_ids: list[str], params: Optional[dict[str, Any]] = None) -> FilterResult:
        """Apply a custom chain of filters."""
        start_time = time.time()
        original_size = len(json.dumps(data, default=str))
        applied_filters = []

        try:
            result = data
            step_results = []

            for i, filter_id in enumerate(filter_ids, 1):
                filter_def = self.filter_library.get_filter_by_id(filter_id)
                if not filter_def:
                    raise ValueError(f"Filter '{filter_id}' not found")

                if filter_def.filter_type == "chain":
                    raise ValueError(f"Cannot include chain filter '{filter_id}' in custom chain")

                step_start_size = len(json.dumps(result, default=str))
                result = self._apply_single_filter(result, filter_def, params or {})
                step_end_size = len(json.dumps(result, default=str))

                step_reduction = (
                    ((step_start_size - step_end_size) / step_start_size * 100) if step_start_size > 0 else 0.0
                )

                step_results.append({
                    "step_order": i,
                    "filter_id": filter_id,
                    "size_before": step_start_size,
                    "size_after": step_end_size,
                    "reduction_percent": step_reduction,
                })

                applied_filters.append(filter_id)
                logger.debug(f"Custom chain step {i} ({filter_id}): {step_reduction:.1f}% reduction")

            final_size = len(json.dumps(result, default=str))
            total_reduction = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0.0
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=True,
                data=result,
                original_size_bytes=original_size,
                final_size_bytes=final_size,
                reduction_percent=total_reduction,
                execution_time_ms=execution_time,
                filters_applied=applied_filters,
                metadata={"chain_type": "custom", "step_results": step_results},
            )

        except Exception as e:
            logger.exception(f"Error applying custom filter chain {filter_ids}: {e}")
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=False,
                data=data,
                original_size_bytes=original_size,
                final_size_bytes=original_size,
                reduction_percent=0.0,
                execution_time_ms=execution_time,
                filters_applied=applied_filters,
                error=str(e),
            )

    def apply_custom_filter(self, data: Any, query: str) -> FilterResult:
        """Apply a custom JSON Query expression."""
        start_time = time.time()
        original_size = len(json.dumps(data, default=str))

        try:
            from jsonquerylang import jsonquery

            result = jsonquery(data, query)

            final_size = len(json.dumps(result, default=str))
            reduction_percent = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0.0
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=True,
                data=result,
                original_size_bytes=original_size,
                final_size_bytes=final_size,
                reduction_percent=reduction_percent,
                execution_time_ms=execution_time,
                filters_applied=["custom"],
                metadata={"custom_query": query},
            )

        except ImportError:
            return FilterResult(
                success=False,
                data=data,
                original_size_bytes=original_size,
                final_size_bytes=original_size,
                reduction_percent=0.0,
                execution_time_ms=0.0,
                filters_applied=[],
                error="jsonquerylang library not installed",
            )
        except Exception as e:
            logger.exception(f"Error applying custom filter: {e}")
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                success=False,
                data=data,
                original_size_bytes=original_size,
                final_size_bytes=original_size,
                reduction_percent=0.0,
                execution_time_ms=execution_time,
                filters_applied=[],
                error=str(e),
            )

    def _apply_single_filter(self, data: Any, filter_def: FilterDefinition, params: dict[str, Any]) -> Any:
        """Apply a single filter definition to data."""
        try:
            from jsonquerylang import jsonquery
        except ImportError:
            raise ImportError("jsonquerylang library is required for filter operations")

        # Merge provided params with filter defaults
        final_params = {}
        for param_name, param_config in filter_def.parameters.items():
            if param_name in params:
                final_params[param_name] = params[param_name]
            elif param_config.get("default") is not None:
                final_params[param_name] = param_config["default"]
            elif param_config.get("required", False):
                raise ValueError(f"Required parameter '{param_name}' not provided for filter '{filter_def.id}'")

        # Substitute parameters in query string (only actual parameters, not JSON syntax)
        query = filter_def.query

        # Only substitute parameters that are actually defined in filter_def.parameters
        if filter_def.parameters:
            for param_name in filter_def.parameters:
                if param_name in final_params:
                    # Use a more precise regex that matches {param_name} but not JSON syntax
                    pattern = r"\{" + re.escape(param_name) + r"\}"
                    replacement = str(final_params[param_name])
                    query = re.sub(pattern, replacement, query)

        # Apply the filter
        return jsonquery(data, query)

    def get_available_filters(
        self, endpoint: str = "", category: str = "", filter_type: str = "", search_term: str = ""
    ) -> dict[str, Any]:
        """Get available filters with metadata for discovery."""
        filters = self.filter_library.search_filters(
            endpoint=endpoint, category=category, filter_type=filter_type, search_term=search_term
        )

        # Group filters by type
        grouped_filters = {"record": [], "field": [], "chain": []}

        for filter_def in filters:
            filter_info = {
                "id": filter_def.id,
                "name": filter_def.name,
                "description": filter_def.description,
                "category": filter_def.category,
                "estimated_reduction_percent": filter_def.estimated_reduction_percent,
                "compatible_endpoints": filter_def.compatible_endpoints,
                "parameters": filter_def.parameters,
                "examples": filter_def.examples,
                "tags": filter_def.tags,
            }

            if filter_def.filter_type == "chain" and filter_def.chain_steps:
                filter_info["chain_steps"] = [
                    {"order": step["order"], "filter_id": step["filter_id"]} for step in filter_def.chain_steps
                ]

            grouped_filters[filter_def.filter_type].append(filter_info)

        return {
            "total_filters": len(filters),
            "filters_by_type": {filter_type: len(filter_list) for filter_type, filter_list in grouped_filters.items()},
            "filters": grouped_filters,
            "search_criteria": {
                "endpoint": endpoint,
                "category": category,
                "filter_type": filter_type,
                "search_term": search_term,
            },
        }

    def get_default_reduction_filter(self, endpoint: str) -> Optional[str]:
        """Get a default data reduction filter for an endpoint."""
        # Look for field filters that provide good reduction
        field_filters = self.filter_library.get_field_filters(endpoint)

        # Prefer filters with high estimated reduction
        best_filter = None
        best_reduction = 0

        for filter_def in field_filters:
            if filter_def.estimated_reduction_percent and filter_def.estimated_reduction_percent > best_reduction:
                best_filter = filter_def.id
                best_reduction = filter_def.estimated_reduction_percent

        return best_filter

    def apply_enhanced_filtering(
        self,
        data: Any,
        filter_id: str = "",
        filter_chain: str = "",
        custom_filter: str = "",
        filter_params: str = "{}",
        reduce_response: bool = False,
        endpoint: str = "",
    ) -> dict[str, Any]:
        """
        Apply enhanced filtering with multiple options.
        This is the main entry point for MCP tool integration.
        """
        try:
            params = json.loads(filter_params) if filter_params else {}
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "invalid_parameters",
                "message": "filter_params must be valid JSON",
                "original_data": data,
            }

        result = None

        try:
            if filter_chain:
                # Process filter chain (comma-separated list)
                chain_ids = [id.strip() for id in filter_chain.split(",")]

                if len(chain_ids) == 1:
                    # Single filter (might be a predefined chain)
                    result = self.apply_filter_by_id(data, chain_ids[0], params)
                else:
                    # Custom chain of multiple filters
                    result = self.apply_custom_chain(data, chain_ids, params)

            elif filter_id:
                # Single filter application
                result = self.apply_filter_by_id(data, filter_id, params)

            elif custom_filter:
                # Custom JSON Query expression
                result = self.apply_custom_filter(data, custom_filter)

            elif reduce_response and endpoint:
                # Apply default reduction filter
                default_filter_id = self.get_default_reduction_filter(endpoint)
                if default_filter_id:
                    result = self.apply_filter_by_id(data, default_filter_id, params)
                else:
                    # No default filter available, return original data
                    result = FilterResult(
                        success=True,
                        data=data,
                        original_size_bytes=len(json.dumps(data, default=str)),
                        final_size_bytes=len(json.dumps(data, default=str)),
                        reduction_percent=0.0,
                        execution_time_ms=0.0,
                        filters_applied=[],
                        metadata={"message": "No default reduction filter available for this endpoint"},
                    )
            else:
                # No filtering requested, return original data
                data_size = len(json.dumps(data, default=str))
                result = FilterResult(
                    success=True,
                    data=data,
                    original_size_bytes=data_size,
                    final_size_bytes=data_size,
                    reduction_percent=0.0,
                    execution_time_ms=0.0,
                    filters_applied=[],
                )

            if not result:
                raise ValueError("No filter result generated")

            # Format response
            response = {
                "success": result.success,
                "data": result.data,
                "metadata": {
                    "original_size_bytes": result.original_size_bytes,
                    "final_size_bytes": result.final_size_bytes,
                    "reduction_percent": round(result.reduction_percent, 1),
                    "execution_time_ms": round(result.execution_time_ms, 2),
                    "filters_applied": result.filters_applied,
                    "timestamp": datetime.now().isoformat(),
                },
            }

            if result.metadata:
                response["metadata"].update(result.metadata)

            if not result.success:
                response["error"] = result.error

            return response

        except Exception as e:
            logger.exception(f"Enhanced filtering error: {e}")
            return {"success": False, "error": "filter_application_failed", "message": str(e), "original_data": data}
