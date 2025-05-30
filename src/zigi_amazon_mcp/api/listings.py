"""Listings API client for Amazon SP-API FBM operations."""

import logging
from typing import Any, Optional

import requests  # type: ignore[import-untyped]

from ..constants import API_PATHS
from ..exceptions import RateLimitError
from ..utils.validators import (
    validate_marketplace_ids,
    validate_seller_sku,
)
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class ListingsAPIClient(BaseAPIClient):
    """Client for Amazon SP-API Listings operations (primarily for FBM inventory)."""

    def get_api_path(self) -> str:
        """Return the base API path for listings operations."""
        return API_PATHS["listings"]

    def get_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: str,
        issue_locale: str = "en_US",
        included_data: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Get a single listing item details.

        Args:
            seller_id: The seller ID
            sku: The seller SKU
            marketplace_ids: Comma-separated marketplace IDs
            issue_locale: Locale for issue messages
            included_data: Data to include (attributes, issues, offers, fulfillmentAvailability)

        Returns:
            Dict containing the formatted response
        """
        try:
            # Validate inputs
            validation_errors = []

            if not seller_id:
                validation_errors.append("seller_id is required")

            if not validate_seller_sku(sku):
                validation_errors.append(f"Invalid SKU format: {sku}")

            is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
            if not is_valid_marketplace:
                validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")

            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Default included data if not specified
            if included_data is None:
                included_data = ["attributes", "offers", "fulfillmentAvailability"]

            # Build request path and parameters
            path = f"{self.get_api_path()}/{seller_id}/{sku}"
            params = {
                "marketplaceIds": marketplace_ids,
                "issueLocale": issue_locale,
            }

            if included_data:
                params["includedData"] = ",".join(included_data)

            # Make API request
            result = self._make_request("GET", path, params=params)

            # Transform the response
            transformed_item = self._transform_listings_item(result)

            return self._format_success_response(
                transformed_item,
                metadata={
                    "marketplace": marketplace_ids.split(",")[0],
                    "seller_id": seller_id,
                },
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
            logger.exception(f"Unexpected error in get_listings_item: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def patch_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: str,
        patches: list[dict[str, Any]],
        issue_locale: str = "en_US",
    ) -> dict[str, Any]:
        """Update a listing item with patch operations.

        Args:
            seller_id: The seller ID
            sku: The seller SKU
            marketplace_ids: Comma-separated marketplace IDs
            patches: List of patch operations
            issue_locale: Locale for issue messages

        Returns:
            Dict containing the formatted response
        """
        try:
            # Validate inputs
            validation_errors = []

            if not seller_id:
                validation_errors.append("seller_id is required")

            if not validate_seller_sku(sku):
                validation_errors.append(f"Invalid SKU format: {sku}")

            is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
            if not is_valid_marketplace:
                validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")

            if not patches:
                validation_errors.append("patches list cannot be empty")

            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Build request path and parameters
            path = f"{self.get_api_path()}/{seller_id}/{sku}"
            params = {
                "marketplaceIds": marketplace_ids,
                "issueLocale": issue_locale,
            }

            # Prepare request body
            body = {
                "productType": "PRODUCT",
                "patches": patches,
            }

            # Make API request
            result = self._make_request("PATCH", path, params=params, data=body)

            return self._format_success_response(
                result,
                metadata={
                    "marketplace": marketplace_ids.split(",")[0],
                    "seller_id": seller_id,
                    "sku": sku,
                },
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
            logger.exception(f"Unexpected error in patch_listings_item: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def _transform_listings_item(self, api_response: dict[str, Any]) -> dict[str, Any]:
        """Transform raw Listings API response to consistent format.

        Args:
            api_response: Raw response from Listings API

        Returns:
            Transformed item data
        """
        # Extract basic information
        sku = api_response.get("sku", "")
        summary = api_response.get("summaries", [{}])[0] if api_response.get("summaries") else {}
        api_response.get("attributes", {})
        offers = api_response.get("offers", [])
        fulfillment_availability = api_response.get("fulfillmentAvailability", [])

        # Extract product details
        product_name = summary.get("itemName", "")
        asin = summary.get("asin", "")
        condition = summary.get("condition", "Unknown")

        # Extract FBM fulfillment availability
        fbm_availability = None
        for availability in fulfillment_availability:
            if availability.get("fulfillmentChannelCode") == "DEFAULT":  # FBM indicator
                fbm_availability = availability
                break

        # Build transformed response
        transformed = {
            "sku": sku,
            "asin": asin,
            "product_name": product_name,
            "condition": condition,
            "listing_status": summary.get("status", [])
            if isinstance(summary.get("status"), list)
            else summary.get("status", "Unknown"),
            "created_date": summary.get("createdDate"),
            "last_updated": summary.get("lastUpdatedDate"),
        }

        # Add pricing information if available
        if offers:
            offer = offers[0]  # Take first offer
            transformed["price"] = {
                "amount": offer.get("price", {}).get("amount"),
                "currency": offer.get("price", {}).get("currency"),
            }

        # Add FBM fulfillment information
        if fbm_availability:
            transformed["fulfillment_availability"] = {
                "fulfillment_channel_code": fbm_availability.get("fulfillmentChannelCode", "DEFAULT"),
                "quantity": fbm_availability.get("quantity", 0),
                "is_available": fbm_availability.get("isAvailable", False),
                "handling_time": fbm_availability.get("handlingTime", {}).get("max", 0),
                "restock_date": fbm_availability.get("restockDate"),
            }
        else:
            # Default FBM availability structure
            transformed["fulfillment_availability"] = {
                "fulfillment_channel_code": "DEFAULT",
                "quantity": 0,
                "is_available": False,
                "handling_time": None,
                "restock_date": None,
            }

        # Add any issues/warnings
        issues = api_response.get("issues", [])
        if issues:
            transformed["issues"] = [
                {
                    "code": issue.get("code"),
                    "message": issue.get("message"),
                    "severity": issue.get("severity"),
                }
                for issue in issues
            ]

        return transformed

    def _handle_http_error(self, error: requests.HTTPError) -> dict[str, Any]:
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
            error_response = {"raw_response": error.response.text if error.response else "No response"}

        status_code = error.response.status_code if error.response else None

        # Determine error code based on status
        if status_code == 401:
            error_code = "auth_failed"
            message = "Authentication failed. Check your credentials."
        elif status_code == 403:
            error_code = "auth_failed"
            message = "Access forbidden. Check your IAM role permissions."
        elif status_code == 404:
            error_code = "api_error"
            message = "Listing not found."
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
