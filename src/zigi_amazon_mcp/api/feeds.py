"""Feeds API client for Amazon SP-API bulk update operations."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from .base import BaseAPIClient
from ..exceptions import RateLimitError
from ..constants import API_PATHS, DEFAULT_RATE_LIMITS
from ..utils.validators import (
    validate_marketplace_ids,
)

logger = logging.getLogger(__name__)


class FeedsAPIClient(BaseAPIClient):
    """Client for Amazon SP-API Feeds operations (bulk updates)."""

    # Feed types for inventory management
    FEED_TYPES = {
        "INVENTORY_AVAILABILITY": "POST_INVENTORY_AVAILABILITY_DATA",
        "PRODUCT_PRICING": "POST_PRODUCT_PRICING_DATA",
        "FLAT_FILE_LISTINGS": "POST_FLAT_FILE_LISTINGS_DATA",
        "PRODUCT_DATA": "POST_PRODUCT_DATA",
    }

    # Feed document content types
    CONTENT_TYPES = {
        "XML": "text/xml; charset=UTF-8",
        "TEXT": "text/plain; charset=UTF-8",
        "CSV": "text/csv; charset=UTF-8",
        "JSON": "application/json; charset=UTF-8",
    }

    def get_api_path(self) -> str:
        """Return the base API path for feeds operations."""
        return API_PATHS["feeds"]

    def create_feed_document(
        self,
        content_type: str = "XML",
    ) -> Dict[str, Any]:
        """Create a feed document to upload feed data.

        Args:
            content_type: Content type of the feed (XML, TEXT, CSV, JSON)

        Returns:
            Dict containing the feed document ID and upload URL
        """
        try:
            # Validate content type
            if content_type not in self.CONTENT_TYPES:
                return self._format_error_response(
                    "invalid_input",
                    f"Invalid content_type. Valid types: {', '.join(self.CONTENT_TYPES.keys())}",
                )

            # Build request path
            path = "/feeds/2021-06-30/documents"
            
            # Build request body
            body = {
                "contentType": self.CONTENT_TYPES[content_type],
            }

            # Make API request
            result = self._make_request("POST", path, data=body)
            
            return self._format_success_response(
                {
                    "feedDocumentId": result.get("feedDocumentId"),
                    "url": result.get("url"),
                    "contentType": content_type,
                },
                metadata={
                    "content_type": content_type,
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
            logger.error(f"Unexpected error in create_feed_document: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {str(e)}",
            )

    def create_feed(
        self,
        feed_type: str,
        marketplace_ids: str,
        feed_document_id: str,
        feed_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new feed submission.

        Args:
            feed_type: Type of feed to submit
            marketplace_ids: Comma-separated marketplace IDs
            feed_document_id: ID of the uploaded feed document
            feed_options: Additional feed-specific options

        Returns:
            Dict containing the feed ID and submission details
        """
        try:
            # Validate inputs
            validation_errors = []
            
            if feed_type not in self.FEED_TYPES.values():
                validation_errors.append(
                    f"Invalid feed_type. Valid types: {', '.join(self.FEED_TYPES.values())}"
                )
            
            is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
            if not is_valid_marketplace:
                validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")
            
            if not feed_document_id:
                validation_errors.append("feed_document_id is required")
            
            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Build request body
            body: Dict[str, Any] = {
                "feedType": feed_type,
                "marketplaceIds": marketplace_ids.split(","),
                "inputFeedDocumentId": feed_document_id,
            }
            
            if feed_options:
                body["feedOptions"] = feed_options

            # Make API request
            result = self._make_request("POST", self.get_api_path(), data=body)
            
            # Extract feed ID
            feed_id = result.get("feedId", "")
            
            return self._format_success_response(
                {
                    "feedId": feed_id,
                    "feedType": feed_type,
                    "processingStatus": "IN_QUEUE",
                    "createdTime": datetime.now(timezone.utc).isoformat(),
                },
                metadata={
                    "marketplace": marketplace_ids.split(",")[0],
                    "feed_type": feed_type,
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
            logger.error(f"Unexpected error in create_feed: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {str(e)}",
            )

    def get_feed(self, feed_id: str) -> Dict[str, Any]:
        """Get the processing status of a feed.

        Args:
            feed_id: The feed ID to check

        Returns:
            Dict containing the feed status and details
        """
        try:
            if not feed_id:
                return self._format_error_response(
                    "invalid_input",
                    "feed_id is required",
                )

            # Build request path
            path = f"{self.get_api_path()}/{feed_id}"

            # Make API request
            result = self._make_request("GET", path)
            
            # Transform response
            feed_data = self._transform_feed_response(result)
            
            return self._format_success_response(
                feed_data,
                metadata={
                    "feed_id": feed_id,
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
            logger.error(f"Unexpected error in get_feed: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {str(e)}",
            )

    def get_feeds(
        self,
        feed_types: Optional[List[str]] = None,
        processing_statuses: Optional[List[str]] = None,
        marketplace_ids: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Get a list of feeds matching the criteria.

        Args:
            feed_types: List of feed types to filter by
            processing_statuses: List of processing statuses to filter by
            marketplace_ids: Comma-separated marketplace IDs
            created_after: ISO 8601 format date
            created_before: ISO 8601 format date
            max_results: Maximum number of results

        Returns:
            Dict containing the list of feeds
        """
        try:
            # Validate inputs
            validation_errors = []
            
            if marketplace_ids:
                is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
                if not is_valid_marketplace:
                    validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")
            
            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Build query parameters
            params: Dict[str, Any] = {"maxResults": min(max_results, 100)}
            
            if feed_types:
                params["feedTypes"] = ",".join(feed_types)
            if processing_statuses:
                params["processingStatuses"] = ",".join(processing_statuses)
            if marketplace_ids:
                params["marketplaceIds"] = marketplace_ids
            if created_after:
                params["createdAfter"] = created_after
            if created_before:
                params["createdBefore"] = created_before

            # Make API request
            result = self._make_request("GET", self.get_api_path(), params=params)
            
            # Transform feeds list
            feeds = result.get("feeds", [])
            transformed_feeds = [
                self._transform_feed_response(feed) for feed in feeds
            ]
            
            return self._format_success_response(
                {
                    "feeds": transformed_feeds,
                    "count": len(transformed_feeds),
                },
                metadata={
                    "filters_applied": bool(feed_types or processing_statuses or marketplace_ids),
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
            logger.error(f"Unexpected error in get_feeds: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {str(e)}",
            )

    def build_inventory_feed_xml(self, inventory_updates: List[Dict[str, Any]]) -> str:
        """Build XML feed content for inventory updates.

        Args:
            inventory_updates: List of inventory update items, each containing:
                - sku: Seller SKU
                - quantity: Available quantity
                - handling_time: Days to ship (optional)
                - restock_date: ISO 8601 restock date (optional)

        Returns:
            XML string for the inventory feed
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">',
            '<Header>',
            '<DocumentVersion>1.01</DocumentVersion>',
            '<MerchantIdentifier>MERCHANT_ID</MerchantIdentifier>',
            '</Header>',
            '<MessageType>Inventory</MessageType>',
        ]
        
        for idx, item in enumerate(inventory_updates, 1):
            xml_parts.extend([
                f'<Message>',
                f'<MessageID>{idx}</MessageID>',
                f'<OperationType>Update</OperationType>',
                f'<Inventory>',
                f'<SKU>{item["sku"]}</SKU>',
                f'<Quantity>{item["quantity"]}</Quantity>',
            ])
            
            if item.get("handling_time"):
                xml_parts.append(f'<FulfillmentLatency>{item["handling_time"]}</FulfillmentLatency>')
            
            if item.get("restock_date"):
                xml_parts.append(f'<RestockDate>{item["restock_date"]}</RestockDate>')
            
            xml_parts.extend([
                '</Inventory>',
                '</Message>',
            ])
        
        xml_parts.append('</AmazonEnvelope>')
        
        return '\n'.join(xml_parts)

    def _transform_feed_response(self, feed: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw feed response to consistent format.

        Args:
            feed: Raw feed data from API

        Returns:
            Transformed feed data
        """
        return {
            "feedId": feed.get("feedId"),
            "feedType": feed.get("feedType"),
            "marketplaceIds": feed.get("marketplaceIds", []),
            "processingStatus": feed.get("processingStatus"),
            "createdTime": feed.get("createdTime"),
            "processingStartTime": feed.get("processingStartTime"),
            "processingEndTime": feed.get("processingEndTime"),
            "resultFeedDocumentId": feed.get("resultFeedDocumentId"),
        }

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
        elif status_code == 404:
            error_code = "api_error"
            message = "Feed not found."
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