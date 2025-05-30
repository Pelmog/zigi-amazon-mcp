# Comprehensive MCP Server Testing Plan
## Enhanced Filtering System Validation

This document provides a systematic testing plan for the MCP server with enhanced filtering capabilities. Each test includes **DUAL VALIDATION**: both direct MCP server protocol testing and programmatic code testing.

## **CRITICAL TESTING APPROACH**

### **Two-Layer Testing Strategy:**
1. **MCP Protocol Testing**: Test via actual MCP server communication (start server, use MCP client)
2. **Code Testing**: Test underlying Python code directly for validation and debugging

### **Fix-and-Retest Methodology:**
- **When tests fail**: Immediately investigate root cause
- **Fix code**: Write corrective code changes
- **Revalidate**: Re-run both MCP and code tests to confirm fixes
- **Document changes**: Record what was fixed and why

### **Response Validation Requirements:**
- **Exact Response Checking**: Verify JSON structure, field names, data types
- **Content Validation**: Ensure data content matches expectations
- **Error Message Validation**: Confirm error messages are helpful and accurate
- **Performance Validation**: Measure response times and data reduction

---

## Phase 1: MCP Server Protocol Testing

### Test 1.1: MCP Server Startup and Discovery Test
**Prompt**: Test that the MCP server starts correctly and can be discovered via MCP protocol.

**MCP Protocol Steps**:
1. Start MCP server: `cd /path/to/repo && uv run python -m src.zigi_amazon_mcp.server`
2. In separate terminal, test server discovery: `mcp connect stdio python -m src.zigi_amazon_mcp.server`
3. List available tools: Use MCP client to enumerate tools
4. Verify tool signatures and descriptions

**Code Testing Steps**:
1. Import the MCP server: `from src.zigi_amazon_mcp.server import mcp, filter_manager`
2. Check filter manager initialization: `type(filter_manager).__name__`
3. Verify database health: `filter_manager.filter_lib.get_database_stats()`
4. Count imported filters during startup

**Expected Results**:
- ✅ **MCP Protocol**: Server starts and responds to MCP client connections
- ✅ **MCP Protocol**: Tool discovery returns list of all available tools (13+ tools expected)
- ✅ **MCP Protocol**: Tool signatures match expected parameters and descriptions
- ✅ **Code Testing**: Server imports without errors
- ✅ **Code Testing**: FilterManager instance created successfully
- ✅ **Code Testing**: Database status shows "healthy"
- ✅ **Code Testing**: At least 50+ filters imported during startup

**Response Validation**:
- **Tool List Structure**: Verify JSON contains `{"tools": [{"name": "...", "description": "...", "inputSchema": {...}}]}`
- **Required Tools Present**: `get_auth_token`, `get_available_filters`, `get_orders`, `get_inventory_in_stock`, etc.
- **Parameter Schemas**: Each tool has proper parameter definitions with types and descriptions

**If Tests Fail - Fix Actions**:
- **Server won't start**: Check Python environment, dependencies, import errors
- **MCP connection fails**: Verify FastMCP setup, check server.py main() function
- **Tools missing**: Check @mcp.tool() decorators, ensure all tools registered
- **Database errors**: Check SQLite file permissions, table creation, seed data import

**Retest After Fixes**: Re-run both MCP protocol and code tests to confirm fixes work.

### Test 1.2: Authentication Token Flow Test
**Prompt**: Test complete authentication workflow via both MCP protocol and code.

**MCP Protocol Steps**:
1. Call `get_auth_token` via MCP client
2. Extract token from response
3. Use token in subsequent MCP tool calls (`hello_world`, `get_available_filters`)
4. Test invalid token rejection

**Code Testing Steps**:
1. Call `get_auth_token()` directly
2. Validate token format and storage: `token in auth_tokens`
3. Test `validate_auth_token(token)` function
4. Test token extraction logic

**Expected Results**:
- ✅ **MCP Protocol**: `get_auth_token` returns properly formatted response
- ✅ **MCP Protocol**: Token works in subsequent MCP calls
- ✅ **MCP Protocol**: Invalid tokens rejected with proper error messages
- ✅ **Code Testing**: Token format is 64-character hex string
- ✅ **Code Testing**: Token stored in auth_tokens set
- ✅ **Code Testing**: Validation function works correctly

**Response Validation**:
- **Token Response Format**: `"Authentication successful. Your auth token is: [64-char-hex]"`
- **Token Format**: Exactly 64 hexadecimal characters
- **Error Message Format**: Consistent across all tools when auth fails
- **Token Persistence**: Token remains valid throughout session

**If Tests Fail - Fix Actions**:
- **Token format wrong**: Check `secrets.token_hex(32)` call in `get_auth_token()`
- **Auth validation fails**: Fix `validate_auth_token()` function logic
- **Inconsistent error messages**: Standardize error responses across all tools
- **Token not persisting**: Check auth_tokens set management

**Retest After Fixes**: Verify both MCP and code paths work with corrected authentication.

---

## Phase 2: Filter System Core Testing

### Test 2.1: Filter Discovery and Validation Test
**Prompt**: Test comprehensive filter discovery via MCP protocol and validate filter data integrity.

**MCP Protocol Steps**:
1. Get auth token via MCP
2. Call `get_available_filters` with no parameters (get all filters)
3. Call with each filter type: `filter_type="record"`, `filter_type="field"`, `filter_type="chain"`
4. Call with categories: `category="orders"`, `category="inventory"`, `category="common"`
5. Call with endpoint filtering: `endpoint="get_orders"`, `endpoint="get_inventory_in_stock"`
6. Test search functionality: `search_term="high"`

**Code Testing Steps**:
1. Test `filter_manager.get_available_filters()` directly
2. Validate filter database integrity: `filter_manager.filter_lib.get_database_stats()`
3. Query specific filters: `filter_manager.filter_lib.get_filter_by_id("high_value_orders")`
4. Test filter metadata completeness

**Expected Results**:
- ✅ **MCP Protocol**: All filter discovery calls return valid JSON responses
- ✅ **MCP Protocol**: Filter counts match expectations (50+ total filters)
- ✅ **MCP Protocol**: Filter types properly separated (record, field, chain)
- ✅ **MCP Protocol**: Category filtering works correctly
- ✅ **MCP Protocol**: Search functionality returns relevant results
- ✅ **Code Testing**: Database contains expected filter count
- ✅ **Code Testing**: All filters have required metadata fields
- ✅ **Code Testing**: Filter chains properly reference existing filters

**Response Validation**:
- **Filter Response Structure**: `{"total_filters": N, "filters": [...], "categories": {...}, "filter_types": {...}}`
- **Individual Filter Structure**: Each filter has `id`, `name`, `description`, `category`, `filter_type`, `query`, etc.
- **Parameter Validation**: Filter parameters have proper types and defaults
- **Reduction Estimates**: Percentages are reasonable (0-99%)

**If Tests Fail - Fix Actions**:
- **Missing filters**: Check seed data import in `initialize_filter_database()`
- **Wrong filter counts**: Verify JSON seed files in `src/zigi_amazon_mcp/filtering/seed_data/`
- **Invalid metadata**: Fix filter schema in database migration files
- **Search not working**: Debug search logic in FilterLibrary.search_filters()
- **Chain references broken**: Fix chain_steps table foreign key references

**Retest After Fixes**: Re-run filter discovery tests and validate corrected data.

### Test 2.2: Filter Application and Data Reduction Test
**Prompt**: Test actual filter application with real data via MCP protocol and validate data reduction.

**MCP Protocol Steps**:
1. Get auth token via MCP
2. Create sample order data (save to test file)
3. Use MCP to call `get_orders` with `filter_id="order_summary"` (field reduction filter)
4. Use MCP to call `get_orders` with `filter_chain="high_value_order_summary_chain"` (chain filter)
5. Use MCP to call `get_orders` with `custom_filter='map({id: .AmazonOrderId, total: .OrderTotal.Amount})'`
6. Use MCP to call `get_orders` with `reduce_response=true`

**Code Testing Steps**:
1. Test `filter_manager.apply_enhanced_filtering()` directly with sample data
2. Test individual filter application: `filter_manager.apply_filter("order_summary", sample_data)`
3. Test filter chains: `filter_manager.apply_filter_chain(["high_value_orders", "order_summary"], sample_data)`
4. Measure data reduction: Compare original vs filtered data sizes
5. Validate JSON query execution: Test jsonquerylang directly

**Sample Test Data**:
```json
[
  {
    "AmazonOrderId": "123-456-789",
    "OrderStatus": "Shipped",
    "OrderTotal": {"Amount": "150.00", "CurrencyCode": "GBP"},
    "PurchaseDate": "2025-01-30T10:00:00Z",
    "IsPrime": true,
    "ShippingAddress": {"Name": "John Doe", "AddressLine1": "123 Main St", "City": "London"}
  },
  {
    "AmazonOrderId": "234-567-890",
    "OrderStatus": "Pending",
    "OrderTotal": {"Amount": "50.00", "CurrencyCode": "GBP"},
    "PurchaseDate": "2025-01-30T11:00:00Z",
    "IsPrime": false,
    "ShippingAddress": {"Name": "Jane Smith", "AddressLine1": "456 Oak Ave", "City": "Manchester"}
  }
]
```

**Expected Results**:
- ✅ **MCP Protocol**: All filter calls return properly formatted JSON responses
- ✅ **MCP Protocol**: Field reduction filter removes unnecessary fields (address, etc.)
- ✅ **MCP Protocol**: Chain filter achieves higher reduction (90%+ expected)
- ✅ **MCP Protocol**: Custom filter executes correctly
- ✅ **MCP Protocol**: reduce_response applies default reduction
- ✅ **Code Testing**: Filter application succeeds without errors
- ✅ **Code Testing**: Data reduction percentages calculated correctly
- ✅ **Code Testing**: Filtered data maintains required business information

**Response Validation**:
- **Filtered Data Structure**: Verify reduced data maintains logical structure
- **Data Reduction Metrics**: Confirm `reduction_percent` field in metadata
- **Execution Performance**: Filter application completes in <100ms for small datasets
- **Business Logic Preservation**: Critical order information (ID, status, total) preserved
- **Error Handling**: Invalid filters return proper error messages

**Data Reduction Validation**:
- **Field Reduction**: order_summary should reduce ~50-70% of data
- **Chain Reduction**: high_value_order_summary_chain should achieve 90%+ reduction
- **Custom Filter**: Should work equivalent to predefined filters
- **Size Calculation**: Original vs final byte counts should be accurate

**If Tests Fail - Fix Actions**:
- **Filter not applying**: Check filter query syntax in database
- **JSON Query errors**: Debug jsonquerylang usage in FilterManager.apply_filter()
- **Wrong reduction calculation**: Fix size calculation logic
- **Chain execution fails**: Debug FilterManager.apply_filter_chain() method
- **MCP response format wrong**: Check JSON serialization in server.py

**Critical Code Fixes Needed**:
- If reduction calculation is wrong: Update `calculate_data_reduction()` method
- If filtering fails: Fix JSON Query syntax in seed data files
- If chains don't work: Repair chain execution logic in FilterManager
- If MCP responses malformed: Fix response formatting in get_orders/get_inventory tools

**Retest After Fixes**: Verify both MCP and code paths produce correct filtering results with accurate reduction metrics.

---

## Phase 3: Error Handling and Security Testing

### Test 3.1: Comprehensive Error Handling Test
**Prompt**: Test error handling across MCP protocol and code for all failure scenarios.

**MCP Protocol Error Testing**:
1. Call tools with invalid auth tokens via MCP
2. Call `get_available_filters` with malformed parameters
3. Call `get_orders` with invalid filter_id values
4. Call with extremely large custom_filter strings
5. Test network timeouts and connection failures

**Code Error Testing**:
1. Test database connection failures: Corrupt SQLite file
2. Test JSON Query parsing errors: Invalid syntax in filters
3. Test memory exhaustion: Extremely large datasets
4. Test corrupted filter data: Missing required fields
5. Test concurrent access conflicts

**Attack Vector Testing**:
1. **SQL Injection**: Try injecting SQL in filter parameters
2. **JSON Injection**: Malformed JSON in custom filters
3. **Memory Attacks**: Extremely nested JSON structures
4. **DoS Attempts**: Rapid repeated requests

**Expected Results**:
- ❌ **All invalid inputs rejected gracefully**
- ❌ **No system crashes or hangs**
- ❌ **Security attacks blocked**
- ✅ **Clear, helpful error messages returned**
- ✅ **System continues operating after errors**

**Error Message Validation**:
- **Consistent Format**: All errors follow same JSON structure
- **Helpful Content**: Messages explain what went wrong and how to fix
- **No Information Leakage**: Errors don't reveal system internals
- **Proper HTTP Status**: If applicable, correct status codes

**If Tests Fail - Fix Actions**:
- **System crashes**: Add try-catch blocks around critical operations
- **Unclear errors**: Improve error message text and structure
- **Security holes**: Add input validation and sanitization
- **Performance issues**: Add request rate limiting and size limits

**Retest After Fixes**: Ensure all error conditions handled properly without system impact.

---

## Phase 4: End-to-End Production Simulation

### Test 4.1: Real-World Usage Simulation Test
**Prompt**: Simulate complete real-world usage patterns via MCP protocol.

**Complete Workflow Test via MCP**:
1. **Business Scenario 1: Daily Order Analysis**
   - Start MCP server
   - Connect MCP client
   - Get auth token
   - Discover order filters: `get_available_filters(category="orders")`
   - Apply high-value order analysis: `get_orders(filter_chain="high_value_order_summary_chain")`
   - Validate business insights from filtered data

2. **Business Scenario 2: Inventory Monitoring**
   - Get auth token (reuse from scenario 1)
   - Find inventory alerts: `get_available_filters(search_term="stock")`
   - Check low stock: `get_inventory_in_stock(filter_chain="low_stock_alert_chain")`
   - Validate actionable inventory insights

3. **Business Scenario 3: Custom Analysis**
   - Create custom filter for specific business need
   - Apply via custom_filter parameter
   - Compare results with predefined filters
   - Validate custom logic works correctly

**Performance Validation**:
- **Response Times**: All MCP calls complete in <2 seconds
- **Data Reduction**: Achieve 85-99% reduction as promised
- **Memory Usage**: Server memory remains stable
- **Concurrent Access**: Multiple scenarios can run simultaneously

**Business Value Validation**:
- **Actionable Data**: Filtered results provide clear business insights
- **Decision Support**: Data supports specific business decisions
- **Efficiency Gains**: Reduced data transfer improves analysis speed
- **Usability**: Non-technical users can understand filter options

**If Tests Fail - Fix Actions**:
- **Poor performance**: Optimize filter execution and database queries
- **Unclear results**: Improve filter design and documentation
- **Business logic wrong**: Fix filter queries to match business requirements
- **Usability issues**: Improve filter naming and descriptions

**Retest After Fixes**: Verify complete workflows provide business value efficiently.

---

## **CRITICAL SUCCESS CRITERIA**

### **Must Pass - System Breaking Issues**:
- ❌ **MCP Server won't start**: Fix immediately, blocking issue
- ❌ **Authentication completely broken**: Security critical
- ❌ **Database corruption**: Data integrity critical
- ❌ **Filter application fails**: Core functionality broken
- ❌ **Security vulnerabilities**: Production blockers

### **Should Pass - Important but Not Blocking**:
- ⚠️ **Slower than expected performance**: Optimize but not blocking
- ⚠️ **Some filter edge cases fail**: Fix but not critical
- ⚠️ **Documentation inaccuracies**: Update but not blocking
- ⚠️ **Minor UI/UX issues**: Improve but not critical

### **Performance Targets**:
- ✅ **Data Reduction**: 85-99% as designed
- ✅ **Response Time**: <2 seconds for typical operations
- ✅ **Reliability**: 99%+ uptime during testing
- ✅ **Accuracy**: 100% accuracy in business logic

### **Production Readiness Checklist**:
- [ ] MCP server starts and responds correctly
- [ ] All authentication flows work
- [ ] Filter discovery returns complete, accurate data
- [ ] Filter application achieves target data reduction
- [ ] Error handling prevents system crashes
- [ ] Security testing passes all checks
- [ ] End-to-end workflows provide business value
- [ ] Performance meets production requirements
- [ ] Documentation is accurate and helpful

---

## **IMMEDIATE ACTION PROTOCOL**

### **When Tests Fail**:
1. **STOP** further testing immediately
2. **DOCUMENT** exact failure scenario and error messages
3. **INVESTIGATE** root cause using both MCP and code approaches
4. **FIX** identified issues in code
5. **RETEST** both MCP protocol and code paths
6. **VERIFY** fix resolves issue without breaking other functionality
7. **CONTINUE** with remaining tests only after fix confirmed

### **Priority Order for Fixes**:
1. **Security Issues** - Fix immediately
2. **System Crashes** - Fix immediately
3. **Core Functionality Failures** - Fix before proceeding
4. **Performance Issues** - Fix if blocking business requirements
5. **Usability Issues** - Fix if time permits

**This comprehensive testing plan ensures both MCP protocol functionality and underlying code correctness through systematic dual validation and immediate fix-and-retest methodology.**
