"""Constants and configuration for Amazon SP-API."""

from datetime import timedelta
from typing import Dict, Any

# Marketplace configuration
MARKETPLACES = {
    "UK": {
        "id": "A1F83G8C2ARO7P",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "GBP",
        "country_code": "GB",
    },
    "US": {
        "id": "ATVPDKIKX0DER",
        "endpoint": "https://sellingpartnerapi-na.amazon.com",
        "region": "us-east-1",
        "currency": "USD",
        "country_code": "US",
    },
    "CA": {
        "id": "A2EUQ1WTGCTBG2",
        "endpoint": "https://sellingpartnerapi-na.amazon.com",
        "region": "us-east-1",
        "currency": "CAD",
        "country_code": "CA",
    },
    "DE": {
        "id": "A1PA6795UKMFR9",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "EUR",
        "country_code": "DE",
    },
    "FR": {
        "id": "A13V1IB3VIYZZH",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "EUR",
        "country_code": "FR",
    },
    "IT": {
        "id": "APJ6JRA9NG5V4",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "EUR",
        "country_code": "IT",
    },
    "ES": {
        "id": "A1RKKUPIHCS9HS",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1",
        "currency": "EUR",
        "country_code": "ES",
    },
    "JP": {
        "id": "A1VC38T7YXB528",
        "endpoint": "https://sellingpartnerapi-fe.amazon.com",
        "region": "us-west-2",
        "currency": "JPY",
        "country_code": "JP",
    },
    "AU": {
        "id": "A39IBJ37TRP1C6",
        "endpoint": "https://sellingpartnerapi-fe.amazon.com",
        "region": "us-west-2",
        "currency": "AUD",
        "country_code": "AU",
    },
}

# Valid marketplace IDs (extracted from MARKETPLACES)
VALID_MARKETPLACE_IDS = {marketplace["id"] for marketplace in MARKETPLACES.values()}

# Cache TTLs by data type
CACHE_TTLS = {
    "inventory": timedelta(minutes=5),      # Changes frequently
    "listings": timedelta(minutes=15),      # More stable
    "pricing": timedelta(minutes=1),        # Very dynamic
    "catalog": timedelta(hours=1),          # Rarely changes
    "orders": None,                         # Never cache orders
}

# SP-API Error Codes
ERROR_CODES = {
    "auth_failed": "Authentication issues",
    "rate_limit_exceeded": "429 errors",
    "invalid_input": "Validation failures",
    "api_error": "SP-API returned an error",
    "network_error": "Connection issues",
    "unexpected_error": "Unhandled exceptions",
}

# API Paths
API_PATHS = {
    "orders": "/orders/v0/orders",
    "order_detail": "/orders/v0/orders/{order_id}",
    "inventory_summaries": "/fba/inventory/v1/summaries",
    "listings": "/listings/2021-08-01/items",
    "feeds": "/feeds/2021-06-30/feeds",
    "reports": "/reports/2021-06-30/reports",
    "pricing": "/product-pricing/v0/price",
}

# Default request timeout (seconds)
DEFAULT_TIMEOUT = 30

# Default rate limits (requests per second, burst capacity)
DEFAULT_RATE_LIMITS = {
    "orders": (10, 30),
    "inventory": (5, 10),
    "feeds": (15, 30),
    "reports": (15, 30),
    "pricing": (10, 20),
}

# Fulfillment types
FULFILLMENT_TYPES = ["FBA", "FBM", "ALL"]

# Order statuses
ORDER_STATUSES = [
    "PendingAvailability",
    "Pending",
    "Unshipped",
    "PartiallyShipped",
    "Shipped",
    "Canceled",
    "Unfulfillable",
    "InvoiceUnconfirmed",
    "Canceling",
]

# Product conditions
PRODUCT_CONDITIONS = [
    "NewItem",
    "UsedLikeNew",
    "UsedVeryGood",
    "UsedGood",
    "UsedAcceptable",
    "CollectibleLikeNew",
    "CollectibleVeryGood",
    "CollectibleGood",
    "CollectibleAcceptable",
    "Refurbished",
]