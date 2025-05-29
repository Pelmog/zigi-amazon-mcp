"""Input validation utilities for SP-API parameters."""

from datetime import datetime
from typing import Any, Dict, List

from ..constants import VALID_MARKETPLACE_IDS, FBM_CONFIG


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


def validate_handling_time(handling_time: int) -> bool:
    """Validate FBM handling time (days to ship).

    Args:
        handling_time: Number of days to ship

    Returns:
        True if handling time is valid
    """
    return isinstance(handling_time, int) and (
        FBM_CONFIG["MIN_HANDLING_TIME"] <= handling_time <= FBM_CONFIG["MAX_HANDLING_TIME"]
    )


def validate_restock_date(restock_date: str) -> bool:
    """Validate FBM restock date.

    Args:
        restock_date: ISO 8601 format restock date

    Returns:
        True if restock date is valid and in the future
    """
    if not restock_date:
        return False
        
    if not validate_iso8601_date(restock_date):
        return False
    
    try:
        # Parse the date
        if restock_date.endswith('Z'):
            restock_datetime = datetime.fromisoformat(restock_date.replace('Z', '+00:00'))
        else:
            restock_datetime = datetime.fromisoformat(restock_date)
        
        # Check if it's in the future
        return restock_datetime > datetime.now(restock_datetime.tzinfo)
    except (ValueError, TypeError):
        return False


def validate_fbm_quantity(quantity: int) -> bool:
    """Validate FBM inventory quantity.

    Args:
        quantity: Inventory quantity

    Returns:
        True if quantity is valid
    """
    return isinstance(quantity, int) and quantity >= 0


def validate_bulk_inventory_updates(updates: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """Validate bulk inventory update items.

    Args:
        updates: List of inventory update items

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not updates:
        errors.append("Update list cannot be empty")
        return False, errors
    
    if len(updates) > FBM_CONFIG["MAX_BULK_UPDATE_SIZE"]:
        errors.append(f"Too many updates. Maximum allowed: {FBM_CONFIG['MAX_BULK_UPDATE_SIZE']}")
    
    for idx, update in enumerate(updates):
        # Check required fields
        if "sku" not in update:
            errors.append(f"Item {idx}: Missing required field 'sku'")
        elif not validate_seller_sku(update["sku"]):
            errors.append(f"Item {idx}: Invalid SKU format")
        
        if "quantity" not in update:
            errors.append(f"Item {idx}: Missing required field 'quantity'")
        elif not validate_fbm_quantity(update["quantity"]):
            errors.append(f"Item {idx}: Invalid quantity")
        
        # Check optional fields
        if "handling_time" in update and not validate_handling_time(update["handling_time"]):
            errors.append(f"Item {idx}: Invalid handling time")
        
        if "restock_date" in update and not validate_restock_date(update["restock_date"]):
            errors.append(f"Item {idx}: Invalid restock date")
    
    return len(errors) == 0, errors