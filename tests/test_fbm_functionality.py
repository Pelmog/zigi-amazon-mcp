"""Unit tests for FBM inventory functionality."""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from zigi_amazon_mcp.api.feeds import FeedsAPIClient
from zigi_amazon_mcp.api.listings import ListingsAPIClient
from zigi_amazon_mcp.api.reports import ReportsAPIClient
from zigi_amazon_mcp.utils.validators import (
    validate_bulk_inventory_updates,
    validate_fbm_quantity,
    validate_handling_time,
    validate_restock_date,
)


class TestFBMValidators:
    """Test FBM-specific validators."""

    def test_validate_handling_time(self):
        """Test handling time validation."""
        # Valid handling times
        assert validate_handling_time(1) is True
        assert validate_handling_time(2) is True
        assert validate_handling_time(30) is True
        
        # Invalid handling times
        assert validate_handling_time(0) is False
        assert validate_handling_time(31) is False
        assert validate_handling_time(-1) is False
        assert validate_handling_time("2") is False  # type: ignore
        assert validate_handling_time(None) is False  # type: ignore

    def test_validate_restock_date(self):
        """Test restock date validation."""
        # Valid future dates
        future_date = (datetime.now() + timedelta(days=7)).isoformat()
        assert validate_restock_date(future_date) is True
        
        future_date_z = (datetime.now() + timedelta(days=7)).isoformat() + "Z"
        assert validate_restock_date(future_date_z) is True
        
        # Invalid dates
        past_date = (datetime.now() - timedelta(days=7)).isoformat()
        assert validate_restock_date(past_date) is False
        
        assert validate_restock_date("invalid-date") is False
        assert validate_restock_date("") is False
        assert validate_restock_date(None) is False  # type: ignore

    def test_validate_fbm_quantity(self):
        """Test FBM quantity validation."""
        # Valid quantities
        assert validate_fbm_quantity(0) is True
        assert validate_fbm_quantity(1) is True
        assert validate_fbm_quantity(10000) is True
        
        # Invalid quantities
        assert validate_fbm_quantity(-1) is False
        assert validate_fbm_quantity("10") is False  # type: ignore
        assert validate_fbm_quantity(None) is False  # type: ignore
        assert validate_fbm_quantity(1.5) is False  # type: ignore

    def test_validate_bulk_inventory_updates(self):
        """Test bulk inventory update validation."""
        # Valid updates
        valid_updates = [
            {"sku": "SKU-001", "quantity": 10},
            {"sku": "SKU-002", "quantity": 0, "handling_time": 2},
        ]
        is_valid, errors = validate_bulk_inventory_updates(valid_updates)
        assert is_valid is True
        assert errors == []
        
        # Invalid updates - missing required fields
        invalid_updates = [
            {"quantity": 10},  # Missing SKU
            {"sku": "SKU-002"},  # Missing quantity
        ]
        is_valid, errors = validate_bulk_inventory_updates(invalid_updates)
        assert is_valid is False
        assert len(errors) == 2
        
        # Invalid updates - bad values
        invalid_updates = [
            {"sku": "SKU-001", "quantity": -5},
            {"sku": "SKU-002", "quantity": 10, "handling_time": 50},
        ]
        is_valid, errors = validate_bulk_inventory_updates(invalid_updates)
        assert is_valid is False
        assert len(errors) == 2


class TestListingsAPIClient:
    """Test ListingsAPIClient functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock listings client."""
        return ListingsAPIClient(
            "test_token",
            {
                "AccessKeyId": "test_key",
                "SecretAccessKey": "test_secret",
                "SessionToken": "test_session",
            },
        )

    @patch("requests.request")
    def test_get_listings_item_success(self, mock_request, mock_client):
        """Test successful listing retrieval."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sku": "TEST-SKU",
            "summaries": [
                {
                    "marketplaceId": "A1F83G8C2ARO7P",
                    "asin": "B001234567",
                    "productType": "PRODUCT",
                    "itemName": "Test Product",
                }
            ],
            "fulfillmentAvailability": [
                {
                    "fulfillmentChannelCode": "DEFAULT",
                    "quantity": 100,
                    "leadTimeToDays": 2,
                }
            ],
        }
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.get_listings_item(
            "SELLER123",
            "TEST-SKU",
            "A1F83G8C2ARO7P",
            ["fulfillmentAvailability"],
        )

        # Verify
        assert result["success"] is True
        assert result["data"]["sku"] == "TEST-SKU"
        assert result["data"]["fulfillment_availability"]["quantity"] == 100

    @patch("requests.request")
    def test_patch_listings_item_success(self, mock_request, mock_client):
        """Test successful listing update."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sku": "TEST-SKU",
            "status": "ACCEPTED",
            "submissionId": "abc123",
        }
        mock_request.return_value = mock_response

        # Make request
        patches = [
            {
                "op": "replace",
                "path": "/attributes/fulfillment_availability",
                "value": [{"quantity": 50}],
            }
        ]
        result = mock_client.patch_listings_item(
            "SELLER123", "TEST-SKU", "A1F83G8C2ARO7P", patches
        )

        # Verify
        assert result["success"] is True
        assert result["data"]["status"] == "ACCEPTED"


class TestReportsAPIClient:
    """Test ReportsAPIClient functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock reports client."""
        return ReportsAPIClient(
            "test_token",
            {
                "AccessKeyId": "test_key",
                "SecretAccessKey": "test_secret",
                "SessionToken": "test_session",
            },
        )

    @patch("requests.request")
    def test_create_report_success(self, mock_request, mock_client):
        """Test successful report creation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reportId": "REPORT123"}
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.create_report(
            "GET_MERCHANT_LISTINGS_ALL_DATA", "A1F83G8C2ARO7P"
        )

        # Verify
        assert result["success"] is True
        assert result["data"]["reportId"] == "REPORT123"
        assert result["data"]["reportType"] == "GET_MERCHANT_LISTINGS_ALL_DATA"

    @patch("requests.request")
    def test_get_report_success(self, mock_request, mock_client):
        """Test successful report status check."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "reportId": "REPORT123",
            "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
            "processingStatus": "DONE",
            "reportDocumentId": "DOC123",
        }
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.get_report("REPORT123")

        # Verify
        assert result["success"] is True
        assert result["data"]["processingStatus"] == "DONE"
        assert result["data"]["reportDocumentId"] == "DOC123"


class TestFeedsAPIClient:
    """Test FeedsAPIClient functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock feeds client."""
        return FeedsAPIClient(
            "test_token",
            {
                "AccessKeyId": "test_key",
                "SecretAccessKey": "test_secret",
                "SessionToken": "test_session",
            },
        )

    @patch("requests.request")
    def test_create_feed_document_success(self, mock_request, mock_client):
        """Test successful feed document creation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "feedDocumentId": "DOC123",
            "url": "https://s3.amazonaws.com/test-bucket/upload",
        }
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.create_feed_document("XML")

        # Verify
        assert result["success"] is True
        assert result["data"]["feedDocumentId"] == "DOC123"
        assert "url" in result["data"]

    @patch("requests.request")
    def test_create_feed_success(self, mock_request, mock_client):
        """Test successful feed creation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"feedId": "FEED123"}
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.create_feed(
            "POST_INVENTORY_AVAILABILITY_DATA",
            "A1F83G8C2ARO7P",
            "DOC123",
        )

        # Verify
        assert result["success"] is True
        assert result["data"]["feedId"] == "FEED123"
        assert result["data"]["feedType"] == "POST_INVENTORY_AVAILABILITY_DATA"

    def test_build_inventory_feed_xml(self, mock_client):
        """Test XML feed generation."""
        updates = [
            {"sku": "SKU-001", "quantity": 10, "handling_time": 2},
            {
                "sku": "SKU-002",
                "quantity": 0,
                "restock_date": "2025-06-01T00:00:00Z",
            },
        ]

        xml = mock_client.build_inventory_feed_xml(updates)

        # Verify XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<SKU>SKU-001</SKU>" in xml
        assert "<Quantity>10</Quantity>" in xml
        assert "<FulfillmentLatency>2</FulfillmentLatency>" in xml
        assert "<SKU>SKU-002</SKU>" in xml
        assert "<RestockDate>2025-06-01T00:00:00Z</RestockDate>" in xml


class TestErrorHandling:
    """Test error handling across API clients."""

    @pytest.fixture
    def mock_client(self):
        """Create mock listings client for error testing."""
        return ListingsAPIClient(
            "test_token",
            {
                "AccessKeyId": "test_key",
                "SecretAccessKey": "test_secret",
                "SessionToken": "test_session",
            },
        )

    @patch("requests.request")
    def test_rate_limit_error(self, mock_request, mock_client):
        """Test rate limit error handling."""
        # Mock 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"x-amzn-RateLimit-Limit": "60"}
        mock_response.raise_for_status.side_effect = Exception("Rate limited")
        mock_request.return_value = mock_response

        # Make request - should handle rate limit
        with pytest.raises(Exception):
            mock_client._make_request("GET", "/test")

    @patch("requests.request")
    def test_auth_error(self, mock_request, mock_client):
        """Test authentication error handling."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errors": ["Unauthorized"]}
        
        # Create HTTPError
        from requests import HTTPError
        http_error = HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_request.return_value = mock_response

        # Make request
        result = mock_client.get_listings_item(
            "SELLER123", "TEST-SKU", "A1F83G8C2ARO7P"
        )

        # Verify error handling
        assert result["success"] is False
        assert result["error"] == "auth_failed"