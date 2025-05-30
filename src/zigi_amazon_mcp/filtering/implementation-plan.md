# JSON Filtering Implementation Plan

## Overview
This plan outlines the implementation of JSON Query-based filtering functionality for the Amazon MCP Server. The system will allow LLMs to discover and apply pre-defined filters to Amazon SP-API responses.

## 1. Core Architecture

### 1.1 Directory Structure
```
src/zigi_amazon_mcp/filtering/
├── __init__.py
├── filtering-instruction.md          # Already exists
├── implementation-plan.md            # This file
├── filter_library.py                # Filter database operations and metadata
├── filter_manager.py                # Filter application and management
├── database.py                      # Database schema and connection management
├── migrations/                      # Database migrations
│   ├── __init__.py
│   └── 001_initial_schema.sql       # Initial database schema
└── seed_data/                       # Pre-built filter definitions
    ├── __init__.py
    ├── order_filters.json           # Order-specific filters (JSON format)
    ├── inventory_filters.json       # Inventory-specific filters (JSON format)
    ├── listing_filters.json         # Listing-specific filters (JSON format)
    └── common_filters.json          # Shared/generic filters (JSON format)
```

### 1.2 Core Components

#### A. Database Layer (`database.py`)
- SQLite database connection and management
- Database schema definition and migrations
- Connection pooling and transaction management
- Database initialization and seeding

#### B. Filter Library (`filter_library.py`)
- Database operations for filter CRUD (Create, Read, Update, Delete)
- Filter search and discovery functionality
- Filter validation and testing
- Filter categorization and tagging
- Import/export functionality for filter definitions

#### C. Filter Manager (`filter_manager.py`)
- Filter retrieval from database
- Filter application to JSON data using retrieved definitions
- Error handling and validation
- Performance optimization and caching

#### D. Seed Data (`seed_data/`)
- Pre-built filter definitions in JSON format
- Organized by domain (orders, inventory, listings, common)
- Version-controlled filter templates
- Database seeding scripts

## 2. Implementation Components

### 2.1 Database Schema

#### A. SQLite Database Tables
```sql
-- Main filters table
CREATE TABLE filters (
    id TEXT PRIMARY KEY,              -- Unique filter identifier
    name TEXT NOT NULL,               -- Human-readable name
    description TEXT NOT NULL,        -- Detailed description
    category TEXT NOT NULL,           -- Filter category (orders, inventory, etc.)
    query TEXT NOT NULL,              -- JSON Query expression
    author TEXT NOT NULL,             -- Filter creator
    version TEXT NOT NULL,            -- Filter version
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE    -- Soft delete flag
);

-- Compatible endpoints table (many-to-many relationship)
CREATE TABLE filter_endpoints (
    filter_id TEXT NOT NULL,
    endpoint_name TEXT NOT NULL,
    PRIMARY KEY (filter_id, endpoint_name),
    FOREIGN KEY (filter_id) REFERENCES filters(id) ON DELETE CASCADE
);

-- Filter parameters table (supports dynamic parameters)
CREATE TABLE filter_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    parameter_type TEXT NOT NULL,     -- 'string', 'number', 'boolean', 'date'
    default_value TEXT,               -- JSON string of default value
    is_required BOOLEAN DEFAULT FALSE,
    description TEXT,
    FOREIGN KEY (filter_id) REFERENCES filters(id) ON DELETE CASCADE,
    UNIQUE(filter_id, parameter_name)
);

-- Filter examples table
CREATE TABLE filter_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id TEXT NOT NULL,
    example_name TEXT NOT NULL,
    description TEXT,
    parameters TEXT,                  -- JSON string of example parameters
    FOREIGN KEY (filter_id) REFERENCES filters(id) ON DELETE CASCADE
);

-- Filter tags table (many-to-many relationship)
CREATE TABLE filter_tags (
    filter_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (filter_id, tag),
    FOREIGN KEY (filter_id) REFERENCES filters(id) ON DELETE CASCADE
);

-- Filter test data table
CREATE TABLE filter_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    test_data TEXT NOT NULL,          -- JSON string of test input data
    expected_result TEXT NOT NULL,    -- JSON string of expected output
    FOREIGN KEY (filter_id) REFERENCES filters(id) ON DELETE CASCADE
);

-- Database metadata table
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### B. Filter Data Model (Python)
```python
@dataclass
class FilterDefinition:
    id: str
    name: str
    description: str
    category: str
    query: str
    author: str
    version: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    compatible_endpoints: List[str]
    parameters: Dict[str, Dict[str, Any]]  # param_name -> {type, default, required, description}
    examples: List[Dict[str, Any]]
    tags: List[str]
    test_cases: List[Dict[str, Any]]

    @classmethod
    def from_database_row(cls, row: Dict[str, Any],
                         endpoints: List[str],
                         parameters: Dict[str, Dict[str, Any]],
                         examples: List[Dict[str, Any]],
                         tags: List[str],
                         test_cases: List[Dict[str, Any]]) -> 'FilterDefinition':
        """Create FilterDefinition from database row and related data."""
        # Implementation details...
```

### 2.2 New MCP Tools

#### A. `get_available_filters` Tool
```python
@mcp.tool()
def get_available_filters(
    auth_token: Annotated[str, "Authentication token"],
    endpoint: Annotated[str, "MCP endpoint name (e.g., 'get_orders', 'get_inventory_in_stock')"] = "",
    category: Annotated[str, "Filter category (e.g., 'orders', 'inventory', 'common')"] = "",
    search_term: Annotated[str, "Search term to find relevant filters"] = ""
) -> str:
    """Returns all available filters for specified endpoint or category."""
```

#### B. Enhanced Existing Tools
- Add optional `filter_id` parameter to existing MCP tools
- Add optional `custom_filter` parameter for ad-hoc filtering
- Maintain backward compatibility

### 2.3 Seed Data Structure

#### A. Order Filters (`order_filters.json`)
```json
{
  "filters": [
    {
      "id": "high_value_orders",
      "name": "High Value Orders",
      "description": "Filter orders above specified monetary threshold",
      "category": "orders",
      "query": "filter(.OrderTotal.Amount > {threshold})",
      "author": "system",
      "version": "1.0.0",
      "compatible_endpoints": ["get_orders", "get_order"],
      "parameters": {
        "threshold": {
          "type": "number",
          "default": 100.0,
          "required": false,
          "description": "Minimum order value threshold"
        }
      },
      "examples": [
        {
          "name": "Orders over £100",
          "description": "Filter orders with value greater than £100",
          "parameters": {"threshold": 100.0}
        },
        {
          "name": "High value orders (£500+)",
          "description": "Filter very high value orders",
          "parameters": {"threshold": 500.0}
        }
      ],
      "tags": ["value", "threshold", "revenue", "high-value"],
      "test_cases": [
        {
          "name": "basic_threshold_test",
          "test_data": [
            {"OrderTotal": {"Amount": 150.0}},
            {"OrderTotal": {"Amount": 50.0}},
            {"OrderTotal": {"Amount": 200.0}}
          ],
          "expected_result": [
            {"OrderTotal": {"Amount": 150.0}},
            {"OrderTotal": {"Amount": 200.0}}
          ]
        }
      ]
    },
    {
      "id": "recent_pending_orders",
      "name": "Recent Pending Orders",
      "description": "Orders with pending status from recent period",
      "category": "orders",
      "query": "filter(.OrderStatus == \"Pending\")",
      "author": "system",
      "version": "1.0.0",
      "compatible_endpoints": ["get_orders"],
      "parameters": {},
      "examples": [
        {
          "name": "All pending orders",
          "description": "Show all orders with pending status",
          "parameters": {}
        }
      ],
      "tags": ["status", "pending", "recent"],
      "test_cases": []
    }
  ]
}
```

#### B. Database Seeding Pattern
```json
{
  "metadata": {
    "version": "1.0.0",
    "created_at": "2025-01-30T00:00:00Z",
    "description": "Initial filter definitions for Amazon MCP Server"
  },
  "filters": [
    // ... filter definitions as shown above
  ]
}
```

## 3. Implementation Steps

### Phase 1: Database Infrastructure
1. **Create database layer** (`database.py`)
   - Implement SQLite database connection management
   - Create database schema and migration system
   - Add connection pooling and transaction support
   - Implement database initialization and health checks

2. **Create filter library** (`filter_library.py`)
   - Implement database CRUD operations for filters
   - Create filter search and discovery functions
   - Add filter validation and testing functionality
   - Implement import/export functionality for JSON seed data

3. **Add dependencies**
   - Update pyproject.toml with jsonquerylang and sqlite3 support
   - Test integration with existing codebase

### Phase 2: Seed Data and Database Setup
1. **Create seed data files**
   - Create order_filters.json with 5-10 common order filters
   - Create inventory_filters.json with 5-10 inventory filters
   - Create common_filters.json with 3-5 reusable filters
   - Create listing_filters.json for future listing operations

2. **Implement database seeding**
   - Create migration scripts for initial schema
   - Implement seeding functionality to populate database from JSON files
   - Add database version management
   - Create backup and restore functionality

### Phase 3: Filter Manager and Application
1. **Create filter manager** (`filter_manager.py`)
   - Implement filter retrieval from database
   - Create filter application logic using jsonquerylang
   - Add parameter substitution system
   - Implement caching for frequently used filters

2. **Add filter validation and testing**
   - Create automated filter testing against test cases
   - Implement filter query validation
   - Add performance monitoring for filter operations
   - Create filter debugging and profiling tools

### Phase 4: MCP Integration
1. **Create get_available_filters tool**
   - Implement filter discovery endpoint with database queries
   - Add search and categorization functionality
   - Include comprehensive documentation and examples

2. **Enhance existing MCP tools**
   - Add filter_id parameter to get_orders
   - Add filter_id parameter to get_inventory_in_stock
   - Add custom_filter parameter for ad-hoc filtering
   - Maintain backward compatibility

3. **Update server.py**
   - Import filter management components
   - Integrate filter application into existing endpoints
   - Add proper error handling for database operations

### Phase 5: Documentation and Testing
1. **Create comprehensive documentation**
   - Update CLAUDE.md with filter usage instructions
   - Create filter development guide with database operations
   - Add usage examples and database management instructions

2. **Add comprehensive testing**
   - Unit tests for all filter components and database operations
   - Integration tests with MCP endpoints
   - Performance testing with large datasets
   - Database migration and seeding tests

3. **Add validation and security**
   - Validate filter queries for security
   - Add rate limiting for filter operations
   - Implement filter caching with database optimization
   - Add database backup and recovery procedures

## 4. Technical Implementation Details

### 4.1 Database Operations
```python
class FilterDatabase:
    """Database operations for filter management."""

    def __init__(self, db_path: str = "filters.db"):
        self.db_path = db_path
        self.connection_pool = sqlite3.connect(db_path, check_same_thread=False)

    def get_filter_by_id(self, filter_id: str) -> Optional[FilterDefinition]:
        """Retrieve a filter by ID with all related data."""
        with self.connection_pool:
            cursor = self.connection_pool.cursor()

            # Get main filter data
            cursor.execute("SELECT * FROM filters WHERE id = ? AND is_active = TRUE", (filter_id,))
            filter_row = cursor.fetchone()
            if not filter_row:
                return None

            # Get related data
            endpoints = self._get_filter_endpoints(cursor, filter_id)
            parameters = self._get_filter_parameters(cursor, filter_id)
            examples = self._get_filter_examples(cursor, filter_id)
            tags = self._get_filter_tags(cursor, filter_id)
            test_cases = self._get_filter_tests(cursor, filter_id)

            return FilterDefinition.from_database_row(
                dict(filter_row), endpoints, parameters, examples, tags, test_cases
            )

    def search_filters(self,
                      endpoint: str = "",
                      category: str = "",
                      search_term: str = "") -> List[FilterDefinition]:
        """Search filters by various criteria."""
        # Implementation with SQL queries and joins...

    def import_filters_from_json(self, json_file_path: str) -> int:
        """Import filters from JSON seed data."""
        # Implementation for bulk import...
```

### 4.2 Filter Parameter Substitution
```python
def apply_filter_with_parameters(filter_def: FilterDefinition, data: Any, params: Dict[str, Any]) -> Any:
    """Apply filter with parameter substitution from database definition."""
    # Merge provided params with database defaults
    final_params = {}
    for param_name, param_config in filter_def.parameters.items():
        if param_name in params:
            final_params[param_name] = params[param_name]
        elif 'default' in param_config:
            final_params[param_name] = param_config['default']
        elif param_config.get('required', False):
            raise ValueError(f"Required parameter '{param_name}' not provided")

    # Substitute parameters in query string
    query = filter_def.query.format(**final_params)

    # Apply jsonquery
    return jsonquery(data, query)
```

### 4.3 MCP Tool Enhancement Pattern
```python
@mcp.tool()
def get_orders(
    auth_token: Annotated[str, "Authentication token"],
    # ... existing parameters ...
    filter_id: Annotated[str, "Filter ID from database to apply to results"] = "",
    filter_params: Annotated[str, "JSON string of filter parameters"] = "{}",
    custom_filter: Annotated[str, "Custom JSON Query expression"] = ""
) -> str:
    """Enhanced get_orders with database-driven filtering support."""

    # ... existing implementation ...

    # Apply filtering if requested
    if filter_id or custom_filter:
        filter_db = FilterDatabase()
        filtered_data = apply_filtering_from_database(
            filter_db, result_data, filter_id, filter_params, custom_filter
        )
        return json.dumps(filtered_data, indent=2)

    return json.dumps(result_data, indent=2)

def apply_filtering_from_database(filter_db: FilterDatabase,
                                data: Any,
                                filter_id: str,
                                filter_params: str,
                                custom_filter: str) -> Any:
    """Apply filtering using database-stored filter definitions."""
    if custom_filter:
        # Apply custom filter directly
        return jsonquery(data, custom_filter)
    elif filter_id:
        # Retrieve filter from database and apply
        filter_def = filter_db.get_filter_by_id(filter_id)
        if not filter_def:
            raise ValueError(f"Filter '{filter_id}' not found in database")

        params = json.loads(filter_params) if filter_params else {}
        return apply_filter_with_parameters(filter_def, data, params)

    return data
```

### 4.4 Database Migration System
```python
class MigrationManager:
    """Database migration management."""

    def __init__(self, db_path: str, migrations_dir: str):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    def run_migrations(self) -> List[str]:
        """Run all pending migrations."""
        executed_migrations = []

        # Create migrations table if not exists
        self._create_migrations_table()

        # Get executed migrations
        executed = self._get_executed_migrations()

        # Run pending migrations
        migration_files = sorted(glob.glob(f"{self.migrations_dir}/*.sql"))
        for migration_file in migration_files:
            migration_name = os.path.basename(migration_file)
            if migration_name not in executed:
                self._execute_migration(migration_file, migration_name)
                executed_migrations.append(migration_name)

        return executed_migrations

### 4.5 Error Handling Strategy
```python
def safe_apply_filter_from_database(filter_db: FilterDatabase,
                                   data: Any,
                                   filter_id: str,
                                   params: Dict[str, Any]) -> Dict[str, Any]:
    """Safely apply filter with comprehensive error handling."""
    try:
        # Retrieve filter from database
        filter_def = filter_db.get_filter_by_id(filter_id)
        if not filter_def:
            return {
                "success": False,
                "error": "filter_not_found",
                "message": f"Filter '{filter_id}' not found in database"
            }

        # Apply filter
        result = apply_filter_with_parameters(filter_def, data, params)
        return {"success": True, "data": result, "filter_id": filter_id}

    except ValueError as e:
        return {
            "success": False,
            "error": "parameter_validation_failed",
            "message": str(e),
            "filter_id": filter_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": "filter_application_failed",
            "message": f"Failed to apply filter: {str(e)}",
            "filter_id": filter_id
        }
```

## 5. Security and Performance Considerations

### 5.1 Security
- **Database Security**:
  - Use parameterized queries to prevent SQL injection
  - Validate filter IDs to prevent unauthorized access
  - Sanitize user-provided custom filters
  - Implement database connection limits
- **Filter Query Security**:
  - Validate JSON Query expressions for safety
  - Limit filter complexity to prevent DoS attacks
  - Implement query timeout mechanisms
  - Restrict access to certain functions in custom filters

### 5.2 Performance
- **Database Optimization**:
  - Use indexes on frequently queried columns (id, category, endpoint)
  - Implement connection pooling for concurrent requests
  - Cache filter definitions in memory after first retrieval
  - Use database transactions for atomic operations
- **Filter Processing**:
  - Cache frequently used filter results
  - Implement lazy evaluation for large datasets
  - Add query optimization for common patterns
  - Monitor filter execution time and memory usage
- **Database Maintenance**:
  - Implement periodic database vacuum for SQLite
  - Monitor database size and performance metrics
  - Create database backup and restoration procedures

## 6. Future Enhancements

### 6.1 Advanced Features
- **Filter Composition**: Combining multiple filters from database
- **Dynamic Filter Generation**: Auto-generate filters based on data analysis
- **Machine Learning Integration**: Filter recommendations based on usage patterns
- **Real-time Analytics**: Filter performance monitoring and optimization
- **Filter Versioning**: Track filter changes and maintain backwards compatibility

### 6.2 Database Enhancements
- **Multi-user Support**: User-specific filters and permissions
- **Filter Sharing**: Community filters and collaborative development
- **Advanced Search**: Full-text search on filter descriptions and examples
- **Filter Dependencies**: Filters that build upon other filters
- **Backup and Sync**: Automated database backup to cloud storage

### 6.3 Management Interface
- **Database Admin Tools**: Web-based interface for filter management
- **Filter Testing Interface**: Interactive filter testing and validation
- **Performance Dashboard**: Monitor filter usage and performance metrics
- **Import/Export Tools**: Bulk filter management and migration

## 7. Success Criteria

### 7.1 Functional Requirements
- LLM can discover available filters for any endpoint
- LLM can apply filters with custom parameters
- All existing MCP functionality remains unchanged
- Filter application is fast and reliable

### 7.2 Quality Requirements
- 100% test coverage for filter components
- Sub-100ms filter application for typical datasets
- Comprehensive documentation and examples
- No security vulnerabilities in filter system

## 8. Dependencies and Prerequisites

### 8.1 New Dependencies
- `jsonquerylang`: JSON Query language implementation
- `sqlite3`: Database operations (part of Python standard library)
- Additional testing dependencies for filter and database validation

### 8.2 Development Prerequisites
- Understanding of JSON Query syntax and capabilities
- Knowledge of Amazon SP-API response structures
- Familiarity with MCP tool development patterns
- SQLite database management and migration concepts
- Understanding of database design and normalization

## 9. Risk Assessment

### 9.1 Technical Risks
- **Database Performance**: Large filter databases could slow query times
  - *Mitigation*: Implement proper indexing, caching, and connection pooling
- **Database Corruption**: SQLite file corruption could lose all filters
  - *Mitigation*: Implement automated backups and recovery procedures
- **Migration Failures**: Database schema changes could break existing filters
  - *Mitigation*: Thorough migration testing and rollback procedures
- **Query Complexity**: Complex filters might be hard to debug
  - *Mitigation*: Provide comprehensive examples and testing tools
- **Security Concerns**: User-provided filters could be malicious
  - *Mitigation*: Implement query validation and sandboxing

### 9.2 Implementation Risks
- **Backward Compatibility**: Changes might break existing integrations
  - *Mitigation*: Maintain strict backward compatibility
- **Database Schema Evolution**: Future changes might require complex migrations
  - *Mitigation*: Design flexible schema with forward compatibility
- **Documentation Debt**: Complex system needs extensive documentation
  - *Mitigation*: Create documentation as part of development process

## 10. Timeline Estimate

- **Phase 1** (Database Infrastructure): 3-4 days
- **Phase 2** (Seed Data and Database Setup): 2-3 days
- **Phase 3** (Filter Manager and Application): 2-3 days
- **Phase 4** (MCP Integration): 1-2 days
- **Phase 5** (Documentation and Testing): 2-3 days

**Total Estimated Time**: 10-15 days

## 11. Database File Management

### 11.1 Database Location
- **Development**: `src/zigi_amazon_mcp/filtering/filters.db`
- **Production**: Configurable via environment variable `FILTER_DB_PATH`
- **Testing**: In-memory database or temporary file

### 11.2 Database Lifecycle
- **Initialization**: Automatic on first run with migration system
- **Seeding**: Populate with initial filters from JSON files
- **Backup**: Scheduled backups to prevent data loss
- **Maintenance**: Periodic optimization and cleanup

This updated plan provides a comprehensive roadmap for implementing database-driven JSON filtering capabilities while maintaining the existing MCP server functionality and ensuring good performance, security, and usability. The database approach offers better scalability, maintainability, and allows for dynamic filter management without code changes.
