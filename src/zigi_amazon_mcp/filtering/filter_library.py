"""
Filter library for managing filter definitions and operations.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .database import FilterDatabase

logger = logging.getLogger(__name__)


@dataclass
class FilterDefinition:
    """Filter definition data model."""

    id: str
    name: str
    description: str
    category: str
    filter_type: str  # 'record', 'field', 'chain'
    query: str
    author: str
    version: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    estimated_reduction_percent: Optional[int]
    compatible_endpoints: list[str]
    parameters: dict[str, dict[str, Any]]
    examples: list[dict[str, Any]]
    tags: list[str]
    test_cases: list[dict[str, Any]]
    chain_steps: Optional[list[dict[str, Any]]] = None  # Only for chain filters

    @classmethod
    def from_database_row(cls, row_data: dict[str, Any]) -> "FilterDefinition":
        """Create FilterDefinition from database row data."""
        return cls(
            id=row_data["id"],
            name=row_data["name"],
            description=row_data["description"],
            category=row_data["category"],
            filter_type=row_data["filter_type"],
            query=row_data["query"],
            author=row_data["author"],
            version=row_data["version"],
            created_at=datetime.fromisoformat(row_data["created_at"]),
            updated_at=datetime.fromisoformat(row_data["updated_at"]),
            is_active=bool(row_data["is_active"]),
            estimated_reduction_percent=row_data.get("estimated_reduction_percent"),
            compatible_endpoints=row_data.get("compatible_endpoints", []),
            parameters=row_data.get("parameters", {}),
            examples=row_data.get("examples", []),
            tags=row_data.get("tags", []),
            test_cases=row_data.get("test_cases", []),
            chain_steps=row_data.get("chain_steps"),
        )


@dataclass
class FilterChain:
    """Filter chain definition."""

    chain_id: str
    name: str
    description: str
    steps: list["FilterStep"]
    estimated_reduction: Optional[int] = None


@dataclass
class FilterStep:
    """Individual step in a filter chain."""

    order: int
    filter_id: str
    filter_def: Optional[FilterDefinition] = None


class FilterLibrary:
    """High-level operations for filter management."""

    def __init__(self, db_path: Optional[str] = None):
        self.db = FilterDatabase(db_path)

    def get_filter_by_id(self, filter_id: str) -> Optional[FilterDefinition]:
        """Get a filter definition by ID."""
        row_data = self.db.get_filter_by_id(filter_id)
        if not row_data:
            return None
        return FilterDefinition.from_database_row(row_data)

    def search_filters(
        self,
        endpoint: str = "",
        category: str = "",
        filter_type: str = "",
        search_term: str = "",
        tags: Optional[list[str]] = None,
    ) -> list[FilterDefinition]:
        """Search for filters matching criteria."""
        rows = self.db.search_filters(endpoint, category, filter_type, search_term, tags)
        return [FilterDefinition.from_database_row(row) for row in rows]

    def get_filters_by_endpoint(self, endpoint: str) -> list[FilterDefinition]:
        """Get all filters compatible with a specific endpoint."""
        return self.search_filters(endpoint=endpoint)

    def get_field_filters(self, endpoint: str = "") -> list[FilterDefinition]:
        """Get all field reduction filters."""
        return self.search_filters(endpoint=endpoint, filter_type="field")

    def get_record_filters(self, endpoint: str = "") -> list[FilterDefinition]:
        """Get all record filtering filters."""
        return self.search_filters(endpoint=endpoint, filter_type="record")

    def get_chain_filters(self, endpoint: str = "") -> list[FilterDefinition]:
        """Get all predefined filter chains."""
        return self.search_filters(endpoint=endpoint, filter_type="chain")

    def get_filter_chain(self, chain_filter_id: str) -> Optional[FilterChain]:
        """Get a complete filter chain with all step definitions."""
        chain_filter = self.get_filter_by_id(chain_filter_id)
        if not chain_filter or chain_filter.filter_type != "chain":
            return None

        # Get step definitions
        steps = []
        if chain_filter.chain_steps:
            for step_data in chain_filter.chain_steps:
                step_filter = self.get_filter_by_id(step_data["filter_id"])
                steps.append(
                    FilterStep(order=step_data["order"], filter_id=step_data["filter_id"], filter_def=step_filter)
                )

        return FilterChain(
            chain_id=chain_filter.id,
            name=chain_filter.name,
            description=chain_filter.description,
            steps=sorted(steps, key=lambda x: x.order),
            estimated_reduction=chain_filter.estimated_reduction_percent,
        )

    def create_filter(self, filter_data: dict[str, Any]) -> bool:
        """Create a new filter in the database."""
        try:
            with self.db.get_connection() as conn:
                # Insert main filter record
                conn.execute(
                    """
                    INSERT INTO filters (
                        id, name, description, category, filter_type, query,
                        author, version, estimated_reduction_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        filter_data["id"],
                        filter_data["name"],
                        filter_data["description"],
                        filter_data["category"],
                        filter_data["filter_type"],
                        filter_data.get("query", ""),
                        filter_data.get("author", "system"),
                        filter_data.get("version", "1.0.0"),
                        filter_data.get("estimated_reduction_percent"),
                    ),
                )

                # Insert compatible endpoints
                for endpoint in filter_data.get("compatible_endpoints", []):
                    conn.execute(
                        "INSERT INTO filter_endpoints (filter_id, endpoint_name) VALUES (?, ?)",
                        (filter_data["id"], endpoint),
                    )

                # Insert parameters
                for param_name, param_config in filter_data.get("parameters", {}).items():
                    conn.execute(
                        """
                        INSERT INTO filter_parameters (
                            filter_id, parameter_name, parameter_type, default_value,
                            is_required, description
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            filter_data["id"],
                            param_name,
                            param_config.get("type", "string"),
                            param_config.get("default"),
                            param_config.get("required", False),
                            param_config.get("description", ""),
                        ),
                    )

                # Insert examples
                for example in filter_data.get("examples", []):
                    conn.execute(
                        """
                        INSERT INTO filter_examples (filter_id, example_name, description, parameters)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            filter_data["id"],
                            example.get("name", ""),
                            example.get("description", ""),
                            json.dumps(example.get("parameters", {})),
                        ),
                    )

                # Insert tags
                for tag in filter_data.get("tags", []):
                    conn.execute("INSERT INTO filter_tags (filter_id, tag) VALUES (?, ?)", (filter_data["id"], tag))

                # Insert test cases
                for test_case in filter_data.get("test_cases", []):
                    conn.execute(
                        """
                        INSERT INTO filter_tests (filter_id, test_name, test_data, expected_result)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            filter_data["id"],
                            test_case.get("name", ""),
                            json.dumps(test_case.get("test_data", {})),
                            json.dumps(test_case.get("expected_result", {})),
                        ),
                    )

                # Insert chain steps if this is a chain filter
                if filter_data.get("filter_type") == "chain":
                    for step in filter_data.get("chain_steps", []):
                        conn.execute(
                            """
                            INSERT INTO filter_chains (chain_filter_id, step_order, step_filter_id)
                            VALUES (?, ?, ?)
                        """,
                            (filter_data["id"], step["order"], step["filter_id"]),
                        )

                conn.commit()
                logger.info(f"Created filter: {filter_data['id']}")
                return True

        except Exception as e:
            logger.exception(f"Failed to create filter {filter_data.get('id', 'unknown')}: {e}")
            return False

    def import_filters_from_json(self, json_file_path: str) -> dict[str, Any]:
        """Import filters from JSON seed data file."""
        try:
            with open(json_file_path, encoding="utf-8") as f:
                data = json.load(f)

            imported = 0
            failed = 0
            errors = []

            # Import regular filters
            for filter_data in data.get("filters", []):
                if self.create_filter(filter_data):
                    imported += 1
                else:
                    failed += 1
                    errors.append(f"Failed to import filter: {filter_data.get('id', 'unknown')}")

            # Import filter chains
            for chain_data in data.get("chains", []):
                if self.create_filter(chain_data):
                    imported += 1
                else:
                    failed += 1
                    errors.append(f"Failed to import chain: {chain_data.get('id', 'unknown')}")

            logger.info(f"Import completed: {imported} successful, {failed} failed")

            return {
                "success": True,
                "imported_count": imported,
                "failed_count": failed,
                "errors": errors,
                "source_file": json_file_path,
            }

        except Exception as e:
            logger.exception(f"Failed to import from {json_file_path}: {e}")
            return {"success": False, "error": str(e), "source_file": json_file_path}

    def export_filters_to_json(
        self, output_file_path: str, category: str = "", filter_type: str = ""
    ) -> dict[str, Any]:
        """Export filters to JSON format."""
        try:
            filters = self.search_filters(category=category, filter_type=filter_type)

            export_data = {
                "metadata": {
                    "version": "1.0.0",
                    "exported_at": datetime.now().isoformat(),
                    "filter_count": len(filters),
                    "category": category or "all",
                    "filter_type": filter_type or "all",
                },
                "filters": [],
            }

            for filter_def in filters:
                filter_dict = {
                    "id": filter_def.id,
                    "name": filter_def.name,
                    "description": filter_def.description,
                    "category": filter_def.category,
                    "filter_type": filter_def.filter_type,
                    "query": filter_def.query,
                    "author": filter_def.author,
                    "version": filter_def.version,
                    "estimated_reduction_percent": filter_def.estimated_reduction_percent,
                    "compatible_endpoints": filter_def.compatible_endpoints,
                    "parameters": filter_def.parameters,
                    "examples": filter_def.examples,
                    "tags": filter_def.tags,
                    "test_cases": filter_def.test_cases,
                }

                if filter_def.filter_type == "chain" and filter_def.chain_steps:
                    filter_dict["chain_steps"] = filter_def.chain_steps

                export_data["filters"].append(filter_dict)

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(filters)} filters to {output_file_path}")

            return {"success": True, "exported_count": len(filters), "output_file": output_file_path}

        except Exception as e:
            logger.exception(f"Failed to export to {output_file_path}: {e}")
            return {"success": False, "error": str(e)}

    def validate_filter(self, filter_def: FilterDefinition) -> dict[str, Any]:
        """Validate a filter definition and run test cases."""
        validation_results = {"valid": True, "errors": [], "warnings": [], "test_results": []}

        # Basic validation
        if not filter_def.id:
            validation_results["errors"].append("Filter ID is required")
        if not filter_def.name:
            validation_results["errors"].append("Filter name is required")
        if not filter_def.query and filter_def.filter_type != "chain":
            validation_results["errors"].append("Filter query is required for non-chain filters")

        # Validate filter type
        if filter_def.filter_type not in ["record", "field", "chain"]:
            validation_results["errors"].append(f"Invalid filter type: {filter_def.filter_type}")

        # Validate chain steps for chain filters
        if filter_def.filter_type == "chain":
            if not filter_def.chain_steps:
                validation_results["errors"].append("Chain filters must have chain_steps defined")
            else:
                for step in filter_def.chain_steps:
                    step_filter = self.get_filter_by_id(step["filter_id"])
                    if not step_filter:
                        validation_results["errors"].append(
                            f"Chain step references non-existent filter: {step['filter_id']}"
                        )

        # Run test cases if available
        if filter_def.test_cases and filter_def.filter_type != "chain":
            try:
                from jsonquerylang import jsonquery

                for test_case in filter_def.test_cases:
                    try:
                        test_data = (
                            json.loads(test_case["test_data"])
                            if isinstance(test_case["test_data"], str)
                            else test_case["test_data"]
                        )
                        expected = (
                            json.loads(test_case["expected_result"])
                            if isinstance(test_case["expected_result"], str)
                            else test_case["expected_result"]
                        )

                        result = jsonquery(test_data, filter_def.query)

                        if result == expected:
                            validation_results["test_results"].append({
                                "test_name": test_case["name"],
                                "status": "passed",
                            })
                        else:
                            validation_results["test_results"].append({
                                "test_name": test_case["name"],
                                "status": "failed",
                                "expected": expected,
                                "actual": result,
                            })
                            validation_results["warnings"].append(f"Test case '{test_case['name']}' failed")

                    except Exception as e:
                        validation_results["test_results"].append({
                            "test_name": test_case["name"],
                            "status": "error",
                            "error": str(e),
                        })
                        validation_results["errors"].append(f"Test case '{test_case['name']}' error: {e!s}")

            except ImportError:
                validation_results["warnings"].append("jsonquerylang not available for test validation")

        if validation_results["errors"]:
            validation_results["valid"] = False

        return validation_results

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics and health information."""
        health = self.db.get_health_check()

        # Add filter type breakdown
        record_filters = len(self.search_filters(filter_type="record"))
        field_filters = len(self.search_filters(filter_type="field"))
        chain_filters = len(self.search_filters(filter_type="chain"))

        # Add category breakdown
        categories = {}
        all_filters = self.search_filters()
        for filter_def in all_filters:
            categories[filter_def.category] = categories.get(filter_def.category, 0) + 1

        health.update({
            "filter_breakdown": {
                "record_filters": record_filters,
                "field_filters": field_filters,
                "chain_filters": chain_filters,
            },
            "category_breakdown": categories,
        })

        return health
