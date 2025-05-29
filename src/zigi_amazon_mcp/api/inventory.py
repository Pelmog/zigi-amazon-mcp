"""Inventory API client for Amazon SP-API interactions."""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from .base import BaseAPIClient, RateLimitError
from ..constants import API_PATHS, FULFILLMENT_TYPES
from ..utils.validators import (
    validate_marketplace_ids, 
    validate_fulfillment_type,
    validate_positive_integer,
)

logger = logging.getLogger(__name__)


class InventoryAPIClient(BaseAPIClient):
    """Client for Amazon SP-API Inventory operations."""

    def get_api_path(self) -> str:
        """Return the base API path for inventory operations."""
        return API_PATHS["inventory_summaries"]

    def get_inventory_summaries(
        self,
        marketplace_ids: str,
        fulfillment_type: str = "ALL",
        details: bool = True,
        max_results: int = 1000,
    ) -> Dict[str, Any]:
        """Get inventory summaries with filtering and pagination.

        Args:
            marketplace_ids: Comma-separated marketplace IDs
            fulfillment_type: Filter by fulfillment type (FBA, FBM, ALL)
            details: Include detailed inventory breakdown
            max_results: Maximum number of results to return

        Returns:
            Dict containing the formatted response
        """
        try:
            # Validate inputs
            validation_errors = self._validate_inputs(
                marketplace_ids, fulfillment_type, max_results
            )
            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Handle FBM limitation
            if fulfillment_type.upper() == "FBM":
                return self._handle_fbm_request(marketplace_ids)

            # Fetch inventory data
            inventory_data = self._fetch_inventory_with_pagination(
                marketplace_ids, details, max_results
            )

            # Filter by fulfillment type if needed
            if fulfillment_type.upper() == "FBA":
                # FBA inventory API already returns only FBA items
                pass

            # Sort by total quantity (highest first)
            inventory_data["inventory"].sort(
                key=lambda x: x["total_quantity"], reverse=True
            )

            # Add summary statistics
            total_products = len(inventory_data["inventory"])
            total_units = sum(item["total_quantity"] for item in inventory_data["inventory"])

            summary = {
                "products_in_stock": total_products,
                "total_units": total_units,
                "marketplace": marketplace_ids,
                "fulfillment_type": fulfillment_type.upper(),
                "timestamp": inventory_data.get("timestamp", ""),
            }

            if fulfillment_type.upper() in ["FBA", "ALL"]:
                summary["note"] = "Shows FBA inventory only"

            return self._format_success_response(
                {
                    "summary": summary,
                    "inventory": inventory_data["inventory"],
                },
                metadata={
                    "marketplace": marketplace_ids.split(",")[0],
                    "total_api_calls": inventory_data.get("api_calls", 1),
                }
            )

        except RateLimitError as e:
            return self._format_error_response(
                "rate_limit_exceeded",
                "Rate limit exceeded. Please wait before making another request.",
                retry_after=e.retry_after,
            )
        except requests.HTTPError as e:
            return self._handle_http_error(e)
        except Exception as e:
            logger.error(f"Unexpected error in get_inventory_summaries: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {str(e)}",
            )

    def _validate_inputs(
        self, marketplace_ids: str, fulfillment_type: str, max_results: int
    ) -> List[str]:
        """Validate input parameters.

        Args:
            marketplace_ids: Comma-separated marketplace IDs
            fulfillment_type: Fulfillment type filter
            max_results: Maximum results to return

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate marketplace IDs
        is_valid, invalid_ids = validate_marketplace_ids(marketplace_ids)
        if not is_valid:
            errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")

        # Validate fulfillment type
        if not validate_fulfillment_type(fulfillment_type):
            errors.append(
                f"Invalid fulfillment_type: {fulfillment_type}. "
                f"Must be one of: {', '.join(FULFILLMENT_TYPES)}"
            )

        # Validate max_results
        if not validate_positive_integer(max_results, min_value=1, max_value=5000):
            errors.append("max_results must be between 1 and 5000")

        return errors

    def _handle_fbm_request(self, marketplace_ids: str) -> Dict[str, Any]:
        """Handle FBM-only requests with appropriate response.

        Args:
            marketplace_ids: Marketplace IDs for the request

        Returns:
            Response indicating FBM limitation
        """
        return self._format_success_response(
            {
                "summary": {
                    "products_in_stock": 0,
                    "total_units": 0,
                    "marketplace": marketplace_ids,
                    "fulfillment_type": "FBM",
                    "note": (
                        "FBM inventory requires Inventory API v0 or Listings API. "
                        "This endpoint uses FBA Inventory API which only returns FBA inventory."
                    ),
                },
                "inventory": [],
            },
            metadata={"marketplace": marketplace_ids.split(",")[0]},
        )

    def _fetch_inventory_with_pagination(
        self, marketplace_ids: str, details: bool, max_results: int
    ) -> Dict[str, Any]:
        """Fetch inventory data with pagination support.

        Args:
            marketplace_ids: Comma-separated marketplace IDs
            details: Include detailed inventory breakdown
            max_results: Maximum results to return

        Returns:
            Dict containing inventory data and metadata
        """
        all_inventory = []
        next_token = None
        api_calls = 0
        latest_payload = {}

        # Prepare base parameters
        params = {
            "marketplaceIds": marketplace_ids,
            "details": "true" if details else "false",
            "granularityType": "Marketplace",
            "granularityId": marketplace_ids.split(",")[0],
        }

        while len(all_inventory) < max_results:
            if next_token:
                params["nextToken"] = next_token

            # Build URL with parameters
            url_path = f"{self.get_api_path()}?{urlencode(params, doseq=True)}"

            # Make API request
            result = self._make_request("GET", url_path)
            api_calls += 1

            # Extract inventory data
            payload = result.get("payload", result)
            latest_payload = payload
            inventory_items = payload.get("inventorySummaries", [])

            # Process and filter inventory items
            for item in inventory_items:
                if len(all_inventory) >= max_results:
                    break

                # Only include items that are in stock
                total_quantity = item.get("totalQuantity", 0)
                if total_quantity > 0:
                    transformed_item = self._transform_inventory_item(item, details)
                    all_inventory.append(transformed_item)

            # Check for next page
            pagination = payload.get("pagination", {})
            next_token = pagination.get("nextToken") or payload.get("nextToken")
            
            if not next_token or len(all_inventory) >= max_results:
                break

        return {
            "inventory": all_inventory,
            "timestamp": latest_payload.get("timestamp", ""),
            "api_calls": api_calls,
        }

    def _transform_inventory_item(self, item: Dict[str, Any], details: bool) -> Dict[str, Any]:
        """Transform raw API inventory item to consistent format.

        Args:
            item: Raw inventory item from API
            details: Whether to include detailed breakdown

        Returns:
            Transformed inventory item
        """
        transformed_item = {
            # Product identifiers
            "asin": item.get("asin"),
            "fn_sku": item.get("fnSku"),
            "seller_sku": item.get("sellerSku"),
            "product_name": item.get("productName"),
            # Stock levels
            "total_quantity": item.get("totalQuantity", 0),
            "condition": item.get("condition", "Unknown"),
            # Last update
            "last_updated": item.get("lastUpdatedTime"),
        }

        # Add detailed breakdown if requested
        if details:
            inventory_details = item.get("inventoryDetails", {})
            
            # Extract unfulfillable quantity safely
            unfulfillable_obj = inventory_details.get("unfulfillableQuantity", {})
            unfulfillable_total = (
                unfulfillable_obj.get("totalUnfulfillableQuantity", 0)
                if isinstance(unfulfillable_obj, dict)
                else 0
            )

            # Extract reserved quantity safely
            reserved_obj = inventory_details.get("reservedQuantity", {})
            reserved_total = (
                reserved_obj.get("totalReservedQuantity", 0)
                if isinstance(reserved_obj, dict)
                else 0
            )

            transformed_item["inventory_breakdown"] = {
                "fulfillable": inventory_details.get("fulfillableQuantity", 0),
                "unfulfillable": unfulfillable_total,
                "reserved": reserved_total,
                "inbound": {
                    "working": inventory_details.get("inboundWorkingQuantity", 0),
                    "shipped": inventory_details.get("inboundShippedQuantity", 0),
                    "receiving": inventory_details.get("inboundReceivingQuantity", 0),
                },
            }

        return transformed_item

    def _handle_http_error(self, error: requests.HTTPError) -> Dict[str, Any]:
        """Handle HTTP errors from SP-API.

        Args:
            error: The HTTP error to handle

        Returns:
            Formatted error response
        """
        error_response = {}
        try:
            if error.response:
                error_response = error.response.json()
        except Exception:
            error_response = {
                "raw_response": error.response.text if error.response else "No response"
            }

        status_code = error.response.status_code if error.response else None
        
        # Determine error code based on status
        if status_code == 401:
            error_code = "auth_failed"
            message = "Authentication failed. Check your credentials."
        elif status_code == 403:
            error_code = "auth_failed"
            message = "Access forbidden. Check your IAM role permissions."
        elif status_code == 429:
            error_code = "rate_limit_exceeded"
            message = "Rate limit exceeded."
        else:
            error_code = "api_error"
            message = "SP-API request failed"

        return self._format_error_response(
            error_code,
            message,
            details=error_response.get("errors", []),
        )