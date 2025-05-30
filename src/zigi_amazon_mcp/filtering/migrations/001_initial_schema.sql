-- Initial filter database schema
-- Migration: 001_initial_schema.sql
-- Description: Create tables for filter management with chaining and data reduction support

-- Main filters table
CREATE TABLE filters (
    id TEXT PRIMARY KEY,              -- Unique filter identifier
    name TEXT NOT NULL,               -- Human-readable name
    description TEXT NOT NULL,        -- Detailed description
    category TEXT NOT NULL,           -- Filter category (orders, inventory, common)
    filter_type TEXT NOT NULL CHECK(filter_type IN ('record', 'field', 'chain')), -- Type of filter
    query TEXT NOT NULL,              -- JSON Query expression (empty for chain types)
    author TEXT NOT NULL,             -- Filter creator
    version TEXT NOT NULL,            -- Filter version
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,   -- Soft delete flag
    estimated_reduction_percent INTEGER DEFAULT NULL  -- Expected data reduction percentage
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
    parameter_type TEXT NOT NULL CHECK(parameter_type IN ('string', 'number', 'boolean', 'date')),
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

-- Filter chains table (for chained filters)
CREATE TABLE filter_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_filter_id TEXT NOT NULL,   -- References filters.id where filter_type='chain'
    step_order INTEGER NOT NULL,     -- Order of execution (1, 2, 3...)
    step_filter_id TEXT NOT NULL,    -- References filters.id for individual step
    FOREIGN KEY (chain_filter_id) REFERENCES filters(id) ON DELETE CASCADE,
    FOREIGN KEY (step_filter_id) REFERENCES filters(id) ON DELETE CASCADE,
    UNIQUE(chain_filter_id, step_order)
);

-- Database metadata table
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_filters_category ON filters(category);
CREATE INDEX idx_filters_filter_type ON filters(filter_type);
CREATE INDEX idx_filters_is_active ON filters(is_active);
CREATE INDEX idx_filter_endpoints_endpoint ON filter_endpoints(endpoint_name);
CREATE INDEX idx_filter_tags_tag ON filter_tags(tag);
CREATE INDEX idx_filter_chains_order ON filter_chains(chain_filter_id, step_order);

-- Insert initial metadata
INSERT INTO metadata (key, value) VALUES
    ('schema_version', '1.0.0'),
    ('created_at', datetime('now')),
    ('description', 'Amazon MCP Filter Database');
