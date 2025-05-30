"""
Database connection and migration management for filter system.
"""

import glob
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MigrationManager:
    """Database migration management."""

    def __init__(self, db_path: str, migrations_dir: str):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    def _create_migrations_table(self, conn: sqlite3.Connection):
        """Create the migrations tracking table if it doesn't exist."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def _get_executed_migrations(self, conn: sqlite3.Connection) -> list[str]:
        """Get list of already executed migrations."""
        cursor = conn.execute("SELECT filename FROM migrations ORDER BY executed_at")
        return [row[0] for row in cursor.fetchall()]

    def _execute_migration(self, conn: sqlite3.Connection, migration_file: str) -> None:
        """Execute a single migration file."""
        migration_name = os.path.basename(migration_file)
        logger.info(f"Executing migration: {migration_name}")

        try:
            with open(migration_file, encoding="utf-8") as f:
                migration_sql = f.read()

            # Execute the migration
            conn.executescript(migration_sql)

            # Record the migration as executed
            conn.execute("INSERT INTO migrations (filename) VALUES (?)", (migration_name,))
            conn.commit()
            logger.info(f"Migration {migration_name} executed successfully")

        except Exception as e:
            conn.rollback()
            logger.exception(f"Failed to execute migration {migration_name}: {e}")
            raise

    def run_migrations(self) -> list[str]:
        """Run all pending migrations."""
        executed_migrations = []

        with sqlite3.connect(self.db_path) as conn:
            # Create migrations table if not exists
            self._create_migrations_table(conn)

            # Get executed migrations
            executed = set(self._get_executed_migrations(conn))

            # Find and run pending migrations
            migration_files = sorted(glob.glob(f"{self.migrations_dir}/*.sql"))

            for migration_file in migration_files:
                migration_name = os.path.basename(migration_file)
                if migration_name not in executed:
                    self._execute_migration(conn, migration_file)
                    executed_migrations.append(migration_name)

        return executed_migrations


class FilterDatabase:
    """Database operations for filter management."""

    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern for database connections."""
        if db_path is None:
            db_path = os.environ.get("FILTER_DB_PATH", "src/zigi_amazon_mcp/filtering/filters.db")

        with cls._lock:
            if db_path not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[db_path] = instance
            return cls._instances[db_path]

    def __init__(self, db_path: Optional[str] = None):
        if hasattr(self, "_initialized"):
            return

        if db_path is None:
            db_path = os.environ.get("FILTER_DB_PATH", "src/zigi_amazon_mcp/filtering/filters.db")

        self.db_path = os.path.abspath(db_path)
        self.migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize database
        self._initialize_database()
        self._initialized = True

    def _initialize_database(self):
        """Initialize database and run migrations."""
        logger.info(f"Initializing filter database at: {self.db_path}")

        # Create database file if it doesn't exist
        if not os.path.exists(self.db_path):
            Path(self.db_path).touch()

        # Run migrations
        migration_manager = MigrationManager(self.db_path, self.migrations_dir)
        executed = migration_manager.run_migrations()

        if executed:
            logger.info(f"Executed {len(executed)} migrations: {', '.join(executed)}")
        else:
            logger.info("Database is up to date")

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: tuple = (), fetch: str = "none") -> Any:
        """Execute a query and return results."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)

            if fetch == "one":
                return cursor.fetchone()
            elif fetch == "all":
                return cursor.fetchall()
            elif fetch == "none":
                conn.commit()
                return cursor.rowcount
            else:
                raise ValueError(f"Invalid fetch mode: {fetch}")

    def get_filter_by_id(self, filter_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a filter by ID with all related data."""
        with self.get_connection() as conn:
            # Get main filter data
            filter_row = conn.execute(
                "SELECT * FROM filters WHERE id = ? AND is_active = TRUE", (filter_id,)
            ).fetchone()

            if not filter_row:
                return None

            # Convert to dict
            filter_data = dict(filter_row)

            # Get related data
            filter_data["compatible_endpoints"] = self._get_filter_endpoints(conn, filter_id)
            filter_data["parameters"] = self._get_filter_parameters(conn, filter_id)
            filter_data["examples"] = self._get_filter_examples(conn, filter_id)
            filter_data["tags"] = self._get_filter_tags(conn, filter_id)
            filter_data["test_cases"] = self._get_filter_tests(conn, filter_id)

            # Get chain steps if this is a chain filter
            if filter_data["filter_type"] == "chain":
                filter_data["chain_steps"] = self._get_filter_chain_steps(conn, filter_id)

            return filter_data

    def _get_filter_endpoints(self, conn: sqlite3.Connection, filter_id: str) -> list[str]:
        """Get compatible endpoints for a filter."""
        cursor = conn.execute("SELECT endpoint_name FROM filter_endpoints WHERE filter_id = ?", (filter_id,))
        return [row[0] for row in cursor.fetchall()]

    def _get_filter_parameters(self, conn: sqlite3.Connection, filter_id: str) -> dict[str, dict[str, Any]]:
        """Get parameters for a filter."""
        cursor = conn.execute(
            "SELECT parameter_name, parameter_type, default_value, is_required, description "
            "FROM filter_parameters WHERE filter_id = ?",
            (filter_id,),
        )

        parameters = {}
        for row in cursor.fetchall():
            param_name = row[0]
            parameters[param_name] = {
                "type": row[1],
                "default": row[2],
                "required": bool(row[3]),
                "description": row[4],
            }
        return parameters

    def _get_filter_examples(self, conn: sqlite3.Connection, filter_id: str) -> list[dict[str, Any]]:
        """Get examples for a filter."""
        cursor = conn.execute(
            "SELECT example_name, description, parameters FROM filter_examples WHERE filter_id = ?", (filter_id,)
        )

        examples = []
        for row in cursor.fetchall():
            examples.append({"name": row[0], "description": row[1], "parameters": row[2]})
        return examples

    def _get_filter_tags(self, conn: sqlite3.Connection, filter_id: str) -> list[str]:
        """Get tags for a filter."""
        cursor = conn.execute("SELECT tag FROM filter_tags WHERE filter_id = ?", (filter_id,))
        return [row[0] for row in cursor.fetchall()]

    def _get_filter_tests(self, conn: sqlite3.Connection, filter_id: str) -> list[dict[str, Any]]:
        """Get test cases for a filter."""
        cursor = conn.execute(
            "SELECT test_name, test_data, expected_result FROM filter_tests WHERE filter_id = ?", (filter_id,)
        )

        tests = []
        for row in cursor.fetchall():
            tests.append({"name": row[0], "test_data": row[1], "expected_result": row[2]})
        return tests

    def _get_filter_chain_steps(self, conn: sqlite3.Connection, chain_filter_id: str) -> list[dict[str, Any]]:
        """Get chain steps for a chain filter."""
        cursor = conn.execute(
            "SELECT step_order, step_filter_id FROM filter_chains WHERE chain_filter_id = ? ORDER BY step_order",
            (chain_filter_id,),
        )

        steps = []
        for row in cursor.fetchall():
            steps.append({"order": row[0], "filter_id": row[1]})
        return steps

    def search_filters(
        self,
        endpoint: str = "",
        category: str = "",
        filter_type: str = "",
        search_term: str = "",
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search filters by various criteria."""

        # Build WHERE clause
        where_clauses = ["f.is_active = TRUE"]
        params = []

        if endpoint:
            where_clauses.append(
                "EXISTS (SELECT 1 FROM filter_endpoints fe WHERE fe.filter_id = f.id AND fe.endpoint_name = ?)"
            )
            params.append(endpoint)

        if category:
            where_clauses.append("f.category = ?")
            params.append(category)

        if filter_type:
            where_clauses.append("f.filter_type = ?")
            params.append(filter_type)

        if search_term:
            where_clauses.append("(f.name LIKE ? OR f.description LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern])

        if tags:
            tag_placeholders = ",".join("?" * len(tags))
            where_clauses.append(
                f"EXISTS (SELECT 1 FROM filter_tags ft WHERE ft.filter_id = f.id AND ft.tag IN ({tag_placeholders}))"
            )
            params.extend(tags)

        where_clause = " AND ".join(where_clauses)

        query = f"""
            SELECT DISTINCT f.* FROM filters f
            WHERE {where_clause}
            ORDER BY f.category, f.name
        """

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_health_check(self) -> dict[str, Any]:
        """Get database health information."""
        try:
            with self.get_connection() as conn:
                # Get table counts
                filter_count = conn.execute("SELECT COUNT(*) FROM filters WHERE is_active = TRUE").fetchone()[0]
                chain_count = conn.execute(
                    "SELECT COUNT(*) FROM filters WHERE filter_type = 'chain' AND is_active = TRUE"
                ).fetchone()[0]

                # Get database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

                # Get metadata
                metadata = {}
                cursor = conn.execute("SELECT key, value FROM metadata")
                for row in cursor.fetchall():
                    metadata[row[0]] = row[1]

                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "database_size_bytes": db_size,
                    "total_filters": filter_count,
                    "chain_filters": chain_count,
                    "metadata": metadata,
                    "checked_at": datetime.now().isoformat(),
                }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "checked_at": datetime.now().isoformat()}
