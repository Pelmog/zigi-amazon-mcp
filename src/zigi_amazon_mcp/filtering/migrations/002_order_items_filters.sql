-- Order Items Filters Migration
-- Migration: 002_order_items_filters.sql
-- Description: Add order items specific filters with comprehensive field, record, and chain filtering

-- Insert order items field filters
INSERT OR REPLACE INTO filters (
    id, name, description, category, filter_type, query, author, version,
    estimated_reduction_percent, created_at, updated_at, is_active
) VALUES
-- Order Items Summary Filter (90% reduction)
(
    'order_items_summary',
    'Order Items Summary',
    'Essential order item information only: ID, ASIN, SKU, title, quantity, and price. Removes shipping details, tax information, gift options, and promotional data. Ideal for basic inventory analysis and sales reporting. Reduces response size by ~90% while preserving core business metrics.',
    'order_items_field',
    'field',
    'map({
        "OrderItemId": .OrderItemId,
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "Title": .Title,
        "Quantity": .QuantityOrdered,
        "Price": .ItemPrice.Amount,
        "Currency": .ItemPrice.CurrencyCode
    })',
    'system',
    '1.0.0',
    90,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Order Items Financial Data (75% reduction)
(
    'order_items_financial',
    'Order Items Financial Data',
    'Complete financial breakdown per order item including all price components, taxes, shipping costs, promotional discounts, and COD fees. Essential for financial reconciliation, tax reporting, and profit margin analysis. Excludes non-financial metadata like product descriptions and gift options.',
    'order_items_field',
    'field',
    'map({
        "OrderItemId": .OrderItemId,
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "ItemPrice": .ItemPrice,
        "ShippingPrice": .ShippingPrice // empty,
        "ItemTax": .ItemTax // empty,
        "ShippingTax": .ShippingTax // empty,
        "PromotionDiscount": .PromotionDiscount // empty,
        "CODFee": .CODFee // empty
    } | with_entries(select(.value != null and .value != empty)))',
    'system',
    '1.0.0',
    75,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Order Items Inventory Tracking (85% reduction)
(
    'order_items_inventory',
    'Order Items Inventory Tracking',
    'Inventory-focused data for stock management and fulfillment tracking. Includes quantity metrics, product condition, and gift status. Perfect for warehouse operations, stock level monitoring, and fulfillment analytics. Removes all pricing and customer information.',
    'order_items_field',
    'field',
    'map({
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "QuantityOrdered": .QuantityOrdered,
        "QuantityShipped": .QuantityShipped,
        "IsGift": .IsGift // false,
        "ConditionId": .ConditionId,
        "ConditionSubtypeId": .ConditionSubtypeId
    })',
    'system',
    '1.0.0',
    85,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Order Items Product Catalog (80% reduction)
(
    'order_items_catalog',
    'Order Items Product Catalog',
    'Product catalog information for listing management and product analysis. Includes product identifiers, titles, and condition details. Useful for catalog optimization, product performance analysis, and listing quality assessment. Excludes all financial and quantity data.',
    'order_items_field',
    'field',
    'map({
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "Title": .Title,
        "ConditionId": .ConditionId,
        "ConditionSubtypeId": .ConditionSubtypeId,
        "ConditionNote": .ConditionNote,
        "IsTransparency": .IsTransparency // false
    })',
    'system',
    '1.0.0',
    80,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- High-Value Items Filter (record filter)
(
    'high_value_items',
    'High-Value Order Items',
    'Filters order items to show only products above a specified price threshold. Default threshold is £50, but can be customized via filter_params. Useful for identifying premium product sales, high-margin items, and expensive product performance. Helps focus analysis on significant revenue contributors.',
    'order_items_record',
    'record',
    'map(select((.ItemPrice.Amount | tonumber) > ($threshold // 50)))',
    'system',
    '1.0.0',
    null,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Gift Items Filter (record filter)
(
    'gift_items_only',
    'Gift Items Only',
    'Filters to show only items marked as gifts. Essential for understanding gift purchasing patterns, seasonal gift trends, and gift-wrapping service utilization. Helps identify products popular as gifts and optimize gift-related marketing strategies.',
    'order_items_record',
    'record',
    'map(select(.IsGift == true))',
    'system',
    '1.0.0',
    null,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Bulk Quantity Items (record filter)
(
    'bulk_quantity_items',
    'Bulk Quantity Items',
    'Filters to show items ordered in bulk quantities. Default minimum is 5 units, customizable via filter_params. Identifies wholesale buyers, bulk purchasers, and popular products for quantity discounts. Useful for inventory planning and identifying business customers.',
    'order_items_record',
    'record',
    'map(select((.QuantityOrdered | tonumber) >= ($min_quantity // 5)))',
    'system',
    '1.0.0',
    null,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Promotional Items (record filter)
(
    'promotional_items',
    'Items with Promotions',
    'Filters to show only items that had promotional discounts applied. Identifies effectiveness of promotional campaigns, discounted product performance, and customer response to offers. Essential for marketing ROI analysis and promotional strategy optimization.',
    'order_items_record',
    'record',
    'map(select(.PromotionDiscount != null and (.PromotionDiscount.Amount | tonumber) > 0))',
    'system',
    '1.0.0',
    null,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- High-Value Items Summary Chain (98% reduction)
(
    'high_value_items_summary_chain',
    'High-Value Items Summary',
    'Combines high-value item filtering with summary field reduction. Shows only expensive items (default £50+) with essential fields only. Perfect for executive reporting on premium product sales. Achieves maximum data reduction (~98%) while focusing on high-impact products.',
    'order_items_chain',
    'chain',
    'map(select((.ItemPrice.Amount | tonumber) > ($threshold // 50))) | map({
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "Title": .Title,
        "Quantity": .QuantityOrdered,
        "Price": .ItemPrice.Amount,
        "Currency": .ItemPrice.CurrencyCode
    })',
    'system',
    '1.0.0',
    98,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Gift Items Financial Chain (95% reduction)
(
    'gift_items_financial_chain',
    'Gift Items Financial Summary',
    'Focuses on gift items with financial data only. Shows revenue from gift purchases, gift-wrapping fees, and gift message usage. Essential for understanding gift market segment profitability and optimizing gift-related services. Combines gift filtering with financial field selection.',
    'order_items_chain',
    'chain',
    'map(select(.IsGift == true)) | map({
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "ItemPrice": .ItemPrice,
        "GiftWrapPrice": .GiftWrapPrice // empty,
        "GiftMessageText": (.GiftMessageText // empty | length > 0)
    } | with_entries(select(.value != null and .value != empty)))',
    'system',
    '1.0.0',
    95,
    datetime('now'),
    datetime('now'),
    TRUE
),

-- Bulk Items Inventory Chain (96% reduction)
(
    'bulk_items_inventory_chain',
    'Bulk Items Inventory Tracking',
    'Identifies bulk orders and tracks their inventory impact. Shows only high-quantity items with inventory-relevant data. Critical for warehouse planning, bulk buyer analysis, and inventory forecasting. Combines quantity filtering with inventory field selection for focused bulk sales analysis.',
    'order_items_chain',
    'chain',
    'map(select((.QuantityOrdered | tonumber) >= ($min_quantity // 5))) | map({
        "ASIN": .ASIN,
        "SellerSKU": .SellerSKU,
        "QuantityOrdered": .QuantityOrdered,
        "QuantityShipped": .QuantityShipped,
        "ConditionId": .ConditionId
    })',
    'system',
    '1.0.0',
    96,
    datetime('now'),
    datetime('now'),
    TRUE
);

-- Insert compatible endpoints for order items filters
INSERT OR REPLACE INTO filter_endpoints (filter_id, endpoint_name) VALUES
('order_items_summary', 'get_order_items'),
('order_items_financial', 'get_order_items'),
('order_items_inventory', 'get_order_items'),
('order_items_catalog', 'get_order_items'),
('high_value_items', 'get_order_items'),
('gift_items_only', 'get_order_items'),
('bulk_quantity_items', 'get_order_items'),
('promotional_items', 'get_order_items'),
('high_value_items_summary_chain', 'get_order_items'),
('gift_items_financial_chain', 'get_order_items'),
('bulk_items_inventory_chain', 'get_order_items');

-- Insert filter parameters for parameterized filters
INSERT OR REPLACE INTO filter_parameters (filter_id, parameter_name, parameter_type, default_value, is_required, description) VALUES
('high_value_items', 'threshold', 'number', '50', FALSE, 'Minimum item price to include in results'),
('bulk_quantity_items', 'min_quantity', 'number', '5', FALSE, 'Minimum quantity to qualify as bulk order'),
('high_value_items_summary_chain', 'threshold', 'number', '50', FALSE, 'Minimum item price to include in results'),
('bulk_items_inventory_chain', 'min_quantity', 'number', '5', FALSE, 'Minimum quantity to qualify as bulk order');

-- Insert filter examples
INSERT OR REPLACE INTO filter_examples (filter_id, example_name, description, parameters) VALUES
('order_items_summary', 'Basic Usage', 'Get essential order item data with 90% size reduction', '{}'),
('order_items_financial', 'Financial Analysis', 'Complete financial breakdown for accounting', '{}'),
('high_value_items', 'Premium Products £100+', 'Show only items worth £100 or more', '{"threshold": 100}'),
('high_value_items', 'Luxury Items £500+', 'Focus on luxury product segment', '{"threshold": 500}'),
('bulk_quantity_items', 'Wholesale Orders (10+)', 'Identify wholesale purchases', '{"min_quantity": 10}'),
('bulk_quantity_items', 'Large Orders (20+)', 'Find very large quantity orders', '{"min_quantity": 20}'),
('high_value_items_summary_chain', 'Executive Dashboard', 'High-value items with minimal data for reports', '{"threshold": 100}'),
('gift_items_financial_chain', 'Gift Revenue Analysis', 'Financial performance of gift segment', '{}'),
('bulk_items_inventory_chain', 'Warehouse Planning', 'Bulk orders impact on inventory', '{"min_quantity": 10}');

-- Insert filter tags
INSERT OR REPLACE INTO filter_tags (filter_id, tag) VALUES
('order_items_summary', 'essential'),
('order_items_summary', 'reporting'),
('order_items_summary', 'high-reduction'),
('order_items_financial', 'financial'),
('order_items_financial', 'accounting'),
('order_items_financial', 'taxes'),
('order_items_inventory', 'inventory'),
('order_items_inventory', 'warehouse'),
('order_items_inventory', 'fulfillment'),
('order_items_catalog', 'catalog'),
('order_items_catalog', 'products'),
('order_items_catalog', 'listings'),
('high_value_items', 'premium'),
('high_value_items', 'high-margin'),
('high_value_items', 'filtering'),
('gift_items_only', 'gifts'),
('gift_items_only', 'seasonal'),
('gift_items_only', 'customer-behavior'),
('bulk_quantity_items', 'wholesale'),
('bulk_quantity_items', 'bulk'),
('bulk_quantity_items', 'business-customers'),
('promotional_items', 'promotions'),
('promotional_items', 'marketing'),
('promotional_items', 'discounts'),
('high_value_items_summary_chain', 'executive'),
('high_value_items_summary_chain', 'premium'),
('high_value_items_summary_chain', 'maximum-reduction'),
('gift_items_financial_chain', 'gifts'),
('gift_items_financial_chain', 'financial'),
('gift_items_financial_chain', 'revenue'),
('bulk_items_inventory_chain', 'bulk'),
('bulk_items_inventory_chain', 'inventory'),
('bulk_items_inventory_chain', 'planning');

-- Insert test cases for key filters
INSERT OR REPLACE INTO filter_tests (filter_id, test_name, test_data, expected_result) VALUES
('order_items_summary', 'Basic Item',
'[{"OrderItemId": "123", "ASIN": "B123", "SellerSKU": "SKU123", "Title": "Test Product", "QuantityOrdered": 2, "ItemPrice": {"Amount": "29.99", "CurrencyCode": "GBP"}, "ShippingPrice": {"Amount": "3.99", "CurrencyCode": "GBP"}}]',
'[{"OrderItemId": "123", "ASIN": "B123", "SellerSKU": "SKU123", "Title": "Test Product", "Quantity": 2, "Price": "29.99", "Currency": "GBP"}]'),

('high_value_items', 'High Value Item',
'[{"OrderItemId": "123", "ItemPrice": {"Amount": "75.00"}}, {"OrderItemId": "456", "ItemPrice": {"Amount": "25.00"}}]',
'[{"OrderItemId": "123", "ItemPrice": {"Amount": "75.00"}}]'),

('gift_items_only', 'Gift Item Filter',
'[{"OrderItemId": "123", "IsGift": true, "Title": "Gift Item"}, {"OrderItemId": "456", "IsGift": false, "Title": "Regular Item"}]',
'[{"OrderItemId": "123", "IsGift": true, "Title": "Gift Item"}]');

-- Update metadata
INSERT OR REPLACE INTO metadata (key, value) VALUES
('order_items_filters_version', '1.0.0'),
('order_items_filters_added', datetime('now')),
('total_order_items_filters', '11');
