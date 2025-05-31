"""Orders API client for Amazon SP-API integration."""

import logging
from datetime import datetime
from typing import Any, Optional

from ..exceptions import RateLimitError
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class OrdersAPIClient(BaseAPIClient):
    """Client for Amazon SP-API Orders endpoints."""

    def get_api_path(self) -> str:
        """Return the base API path for Orders endpoints."""
        return "/orders/v0"

    def get_orders(
        self,
        marketplace_ids: list[str],
        created_after: str,
        created_before: Optional[str] = None,
        order_statuses: Optional[list[str]] = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """
        Retrieve multiple orders from Amazon Seller Central.

        Args:
            marketplace_ids: List of marketplace IDs
            created_after: ISO 8601 date string for orders created after this date
            created_before: Optional ISO 8601 date string for orders created before this date
            order_statuses: Optional list of order statuses to filter by
            max_results: Maximum number of orders to retrieve

        Returns:
            Dict containing orders data

        Raises:
            RateLimitError: When rate limits are exceeded
            SPAPIError: For other API errors
        """
        path = "/orders/v0/orders"
        params = {
            "MarketplaceIds": ",".join(marketplace_ids),
            "CreatedAfter": created_after,
        }

        if created_before:
            params["CreatedBefore"] = created_before

        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)

        # Handle pagination to get up to max_results
        all_orders = []
        next_token = None
        retrieved_count = 0

        while retrieved_count < max_results:
            if next_token:
                params["NextToken"] = next_token

            try:
                response = self._make_request("GET", path, params=params)
                orders = response.get("payload", {}).get("Orders", [])

                # Add orders but don't exceed max_results
                remaining_slots = max_results - retrieved_count
                orders_to_add = orders[:remaining_slots]
                all_orders.extend(orders_to_add)
                retrieved_count += len(orders_to_add)

                # Check for next page
                next_token = response.get("payload", {}).get("NextToken")
                if not next_token or retrieved_count >= max_results:
                    break

                # Remove NextToken from params for next iteration if no more pages
                params.pop("NextToken", None)

            except Exception:
                logger.exception("Error fetching orders")
                raise

        return self._format_success_response(
            {"Orders": all_orders},
            metadata={
                "orders_retrieved": len(all_orders),
                "total_requested": max_results,
                "pagination_complete": next_token is None or retrieved_count >= max_results,
            },
        )

    def get_order(self, order_id: str) -> dict[str, Any]:
        """
        Retrieve details for a single order.

        Args:
            order_id: Amazon Order ID

        Returns:
            Dict containing order data

        Raises:
            RateLimitError: When rate limits are exceeded
            SPAPIError: For other API errors
        """
        path = f"/orders/v0/orders/{order_id}"

        try:
            response = self._make_request("GET", path)
            order_data = response.get("payload", {})

            return self._format_success_response(
                order_data,
                metadata={
                    "order_id": order_id,
                    "retrieved_at": datetime.now().isoformat() + "Z",
                },
            )

        except Exception:
            logger.exception("Error fetching order %s", order_id)
            raise

    def get_order_items(self, order_id: str, marketplace_ids: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Retrieve order items for a specific order.

        This endpoint has strict rate limits: 0.5 requests/second with burst of 30.

        Args:
            order_id: Amazon Order ID
            marketplace_ids: Optional list of marketplace IDs

        Returns:
            Dict containing order items data

        Raises:
            RateLimitError: When rate limits are exceeded (429 status)
            SPAPIError: For other API errors
        """
        path = f"/orders/v0/orders/{order_id}/orderItems"
        params = {}

        if marketplace_ids:
            params["MarketplaceIds"] = ",".join(marketplace_ids)

        try:
            # Apply strict rate limiting for this endpoint
            logger.info(f"Fetching order items for order {order_id}")

            response = self._make_request("GET", path, params=params)
            order_items_data = response.get("payload", {})

            # Get order items list
            order_items = order_items_data.get("OrderItems", [])

            return self._format_success_response(
                order_items_data,
                metadata={
                    "order_id": order_id,
                    "items_count": len(order_items),
                    "retrieved_at": datetime.now().isoformat() + "Z",
                    "rate_limit_info": {
                        "endpoint": "getOrderItems",
                        "rate_limit": "0.5 requests/second",
                        "burst_capacity": 30,
                    },
                },
            )

        except Exception as e:
            logger.exception("Error fetching order items for order %s", order_id)

            # Handle rate limiting specifically for this endpoint
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                retry_after = int(e.response.headers.get("x-amzn-RateLimit-Limit", 120))
                msg = "Rate limit exceeded for getOrderItems endpoint"
                raise RateLimitError(msg, retry_after) from e

            raise

    def get_order_buyer_info(self, order_id: str) -> dict[str, Any]:
        """
        Retrieve buyer information for a specific order.

        Note: This requires additional permissions and is subject to PII restrictions.

        Args:
            order_id: Amazon Order ID

        Returns:
            Dict containing buyer information

        Raises:
            RateLimitError: When rate limits are exceeded
            SPAPIError: For other API errors
        """
        path = f"/orders/v0/orders/{order_id}/buyerInfo"

        try:
            response = self._make_request("GET", path)
            buyer_info_data = response.get("payload", {})

            return self._format_success_response(
                buyer_info_data,
                metadata={
                    "order_id": order_id,
                    "retrieved_at": datetime.now().isoformat() + "Z",
                    "pii_warning": "This endpoint returns PII data. Handle with appropriate security measures.",
                },
            )

        except Exception:
            logger.exception("Error fetching buyer info for order %s", order_id)
            raise

    def get_order_items_buyer_info(self, order_id: str) -> dict[str, Any]:
        """
        Retrieve buyer information for order items.

        Note: This requires additional permissions and is subject to PII restrictions.

        Args:
            order_id: Amazon Order ID

        Returns:
            Dict containing order items buyer information

        Raises:
            RateLimitError: When rate limits are exceeded
            SPAPIError: For other API errors
        """
        path = f"/orders/v0/orders/{order_id}/orderItems/buyerInfo"

        try:
            response = self._make_request("GET", path)
            buyer_info_data = response.get("payload", {})

            return self._format_success_response(
                buyer_info_data,
                metadata={
                    "order_id": order_id,
                    "retrieved_at": datetime.now().isoformat() + "Z",
                    "pii_warning": "This endpoint returns PII data. Handle with appropriate security measures.",
                },
            )

        except Exception:
            logger.exception("Error fetching order items buyer info for order %s", order_id)
            raise
