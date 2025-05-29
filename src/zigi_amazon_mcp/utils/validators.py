"""Input validation utilities for SP-API parameters."""

from datetime import datetime
from typing import List

from ..constants import VALID_MARKETPLACE_IDS


def validate_marketplace_id(marketplace_id: str) -> bool:
    """Validate marketplace ID format and existence.

    Args:
        marketplace_id: The marketplace ID to validate

    Returns:
        True if marketplace ID is valid
    """
    return marketplace_id in VALID_MARKETPLACE_IDS


def validate_marketplace_ids(marketplace_ids: str) -> tuple[bool, List[str]]:
    """Validate comma-separated marketplace IDs.

    Args:
        marketplace_ids: Comma-separated marketplace IDs

    Returns:
        Tuple of (is_valid, list_of_invalid_ids)
    """
    if not marketplace_ids:
        return False, ["marketplace_ids cannot be empty"]
    
    ids = [mid.strip() for mid in marketplace_ids.split(",")]
    invalid_ids = [mid for mid in ids if not validate_marketplace_id(mid)]
    
    return len(invalid_ids) == 0, invalid_ids


def validate_iso8601_date(date_string: str) -> bool:
    """Validate ISO 8601 date format.

    Args:
        date_string: Date string to validate

    Returns:
        True if date format is valid
    """
    try:
        # Handle both with and without 'Z' suffix
        if date_string.endswith('Z'):
            datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(date_string)
        return True
    except (ValueError, TypeError):
        return False


def validate_fulfillment_type(fulfillment_type: str) -> bool:
    """Validate fulfillment type parameter.

    Args:
        fulfillment_type: The fulfillment type to validate

    Returns:
        True if fulfillment type is valid
    """
    return fulfillment_type.upper() in ["FBA", "FBM", "ALL"]


def validate_seller_sku(sku: str) -> bool:
    """Validate seller SKU format.

    Args:
        sku: The seller SKU to validate

    Returns:
        True if SKU format is valid
    """
    if not sku or len(sku.strip()) == 0:
        return False
    
    # SKUs must not contain certain special characters
    forbidden_chars = ['<', '>', ':', '"', '|', '?', '*']
    return not any(char in sku for char in forbidden_chars)


def validate_order_status(status: str) -> bool:
    """Validate order status parameter.

    Args:
        status: The order status to validate

    Returns:
        True if order status is valid
    """
    valid_statuses = [
        "PendingAvailability",
        "Pending",
        "Unshipped",
        "PartiallyShipped", 
        "Shipped",
        "Canceled",
        "Unfulfillable",
        "InvoiceUnconfirmed",
        "Canceling"
    ]
    return status in valid_statuses


def validate_positive_integer(value: int, min_value: int = 1, max_value: int = 1000) -> bool:
    """Validate positive integer within range.

    Args:
        value: The integer to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        True if value is valid
    """
    return isinstance(value, int) and min_value <= value <= max_value