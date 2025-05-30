"""Test suite for sales analytics and reporting MCP tools."""

import json
from unittest.mock import Mock, patch
import pytest
from datetime import datetime, timezone
import gzip

from zigi_amazon_mcp.server import (
    get_sales_and_traffic_report,
    create_report,
    get_report_status,
    get_report_document,
    get_inventory_analytics_report,
    auth_tokens,
)
from zigi_amazon_mcp.api.reports import ReportsAPIClient


class TestSalesAnalyticsTools:
    """Test sales analytics MCP tool functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        # Clear and add test auth token
        auth_tokens.clear()
        self.test_token = "test_auth_token_12345"
        auth_tokens.add(self.test_token)
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'LWA_CLIENT_ID': 'test_client_id',
            'LWA_CLIENT_SECRET': 'test_client_secret',
            'LWA_REFRESH_TOKEN': 'test_refresh_token',
            'AWS_ACCESS_KEY_ID': 'test_access_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
        })
        self.env_patcher.start()
        
    def teardown_method(self):
        """Clean up after each test."""
        self.env_patcher.stop()
        auth_tokens.clear()

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'create_report')
    def test_get_sales_and_traffic_report_success(self, mock_create, mock_aws_creds, mock_access_token):
        """Test successful sales and traffic report creation."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        mock_create.return_value = {
            "success": True,
            "data": {
                "reportId": "report-123",
                "reportType": "GET_SALES_AND_TRAFFIC_REPORT",
                "status": "IN_QUEUE",
                "createdTime": "2025-01-30T10:00:00Z"
            },
            "metadata": {
                "marketplace": "A1F83G8C2ARO7P",
                "report_type": "GET_SALES_AND_TRAFFIC_REPORT"
            }
        }

        # Call function
        result = get_sales_and_traffic_report(
            auth_token=self.test_token,
            marketplace_ids="A1F83G8C2ARO7P",
            start_date="2025-01-01T00:00:00Z",
            end_date="2025-01-30T23:59:59Z",
            granularity="DAY"
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["reportId"] == "report-123"
        assert response["data"]["reportType"] == "GET_SALES_AND_TRAFFIC_REPORT"
        
        # Verify API call parameters
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args["report_type"] == "GET_SALES_AND_TRAFFIC_REPORT"
        assert call_args["marketplace_ids"] == "A1F83G8C2ARO7P"
        assert call_args["report_options"]["reportPeriod"] == "DAY"
        assert call_args["report_options"]["asinGranularity"] == "CHILD"

    def test_get_sales_and_traffic_report_invalid_auth(self):
        """Test sales report with invalid auth token."""
        result = get_sales_and_traffic_report(
            auth_token="invalid_token",
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert response["error"] == "auth_failed"
        assert "Invalid or missing auth token" in response["message"]

    def test_get_sales_and_traffic_report_invalid_granularity(self):
        """Test sales report with invalid granularity."""
        result = get_sales_and_traffic_report(
            auth_token=self.test_token,
            marketplace_ids="A1F83G8C2ARO7P",
            granularity="INVALID"
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert response["error"] == "invalid_input"
        assert "Invalid granularity" in response["message"]

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'create_report')
    def test_create_report_success(self, mock_create, mock_aws_creds, mock_access_token):
        """Test successful generic report creation."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        mock_create.return_value = {
            "success": True,
            "data": {
                "reportId": "report-456",
                "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
                "status": "IN_QUEUE",
                "createdTime": "2025-01-30T10:00:00Z"
            },
            "metadata": {
                "marketplace": "A1F83G8C2ARO7P",
                "report_type": "GET_MERCHANT_LISTINGS_ALL_DATA"
            }
        }

        # Call function
        result = create_report(
            auth_token=self.test_token,
            report_type="GET_MERCHANT_LISTINGS_ALL_DATA",
            marketplace_ids="A1F83G8C2ARO7P"
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["reportId"] == "report-456"
        assert response["data"]["reportType"] == "GET_MERCHANT_LISTINGS_ALL_DATA"

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'get_report')
    def test_get_report_status_success(self, mock_get, mock_aws_creds, mock_access_token):
        """Test successful report status check."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        mock_get.return_value = {
            "success": True,
            "data": {
                "reportId": "report-123",
                "reportType": "GET_SALES_AND_TRAFFIC_REPORT",
                "processingStatus": "DONE",
                "reportDocumentId": "doc-789",
                "createdTime": "2025-01-30T10:00:00Z",
                "processingEndTime": "2025-01-30T10:05:00Z"
            },
            "metadata": {
                "report_id": "report-123"
            }
        }

        # Call function
        result = get_report_status(
            auth_token=self.test_token,
            report_id="report-123"
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["processingStatus"] == "DONE"
        assert response["data"]["reportDocumentId"] == "doc-789"

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'get_report_document')
    @patch('requests.get')
    def test_get_report_document_with_download(self, mock_requests_get, mock_get_doc, mock_aws_creds, mock_access_token):
        """Test report document download and parsing."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        
        # Mock document details
        mock_get_doc.return_value = {
            "success": True,
            "data": {
                "url": "https://example.com/report.gz",
                "compressionAlgorithm": "GZIP",
                "reportDocumentId": "doc-789"
            }
        }
        
        # Create sample report data
        report_data = "sku\tproduct-name\tprice\tquantity\n"
        report_data += "SKU001\tProduct 1\t19.99\t50\n"
        report_data += "SKU002\tProduct 2\t29.99\t30\n"
        
        # Mock compressed content download
        compressed_data = gzip.compress(report_data.encode('utf-8'))
        mock_response = Mock()
        mock_response.content = compressed_data
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # Call function
        result = get_report_document(
            auth_token=self.test_token,
            report_document_id="doc-789",
            download_content=True
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["summary"]["total_rows"] == 2
        assert response["data"]["summary"]["headers"] == ["sku", "product-name", "price", "quantity"]
        assert len(response["data"]["rows"]) == 2
        assert response["data"]["rows"][0]["sku"] == "SKU001"
        assert response["data"]["rows"][1]["product-name"] == "Product 2"

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'get_report_document')
    def test_get_report_document_url_only(self, mock_get_doc, mock_aws_creds, mock_access_token):
        """Test getting report document URL without downloading."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        
        mock_get_doc.return_value = {
            "success": True,
            "data": {
                "url": "https://example.com/report.gz",
                "compressionAlgorithm": "GZIP",
                "reportDocumentId": "doc-789"
            }
        }

        # Call function
        result = get_report_document(
            auth_token=self.test_token,
            report_document_id="doc-789",
            download_content=False
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["url"] == "https://example.com/report.gz"
        assert "rows" not in response["data"]  # Should not have downloaded content

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    @patch.object(ReportsAPIClient, 'create_report')
    def test_get_inventory_analytics_report_success(self, mock_create, mock_aws_creds, mock_access_token):
        """Test inventory analytics report convenience function."""
        # Setup mocks
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = {
            "AccessKeyId": "test_key",
            "SecretAccessKey": "test_secret",
            "SessionToken": "test_session"
        }
        mock_create.return_value = {
            "success": True,
            "data": {
                "reportId": "report-inv-123",
                "reportType": "GET_FBA_INVENTORY_PLANNING_DATA",
                "status": "IN_QUEUE",
                "createdTime": "2025-01-30T10:00:00Z"
            },
            "metadata": {
                "marketplace": "A1F83G8C2ARO7P",
                "report_type": "GET_FBA_INVENTORY_PLANNING_DATA"
            }
        }

        # Call function
        result = get_inventory_analytics_report(
            auth_token=self.test_token,
            report_type="FBA_HEALTH",
            marketplace_ids="A1F83G8C2ARO7P"
        )

        # Parse and verify result
        response = json.loads(result)
        assert response["success"] is True
        assert response["data"]["reportId"] == "report-inv-123"
        assert "instructions" in response["data"]
        assert "next_steps" in response["data"]["instructions"]
        assert response["data"]["instructions"]["report_info"]["type"] == "FBA_HEALTH"
        
        # Verify correct report type mapping
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args["report_type"] == "GET_FBA_INVENTORY_PLANNING_DATA"

    def test_get_inventory_analytics_report_invalid_type(self):
        """Test inventory analytics report with invalid type."""
        result = get_inventory_analytics_report(
            auth_token=self.test_token,
            report_type="INVALID_TYPE",
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert response["error"] == "invalid_input"
        assert "Invalid report_type" in response["message"]

    @patch('zigi_amazon_mcp.server.get_amazon_access_token')
    @patch('zigi_amazon_mcp.server.get_amazon_aws_credentials')
    def test_credential_failure_handling(self, mock_aws_creds, mock_access_token):
        """Test handling of credential failures."""
        # Test LWA token failure
        mock_access_token.return_value = None
        
        result = create_report(
            auth_token=self.test_token,
            report_type="GET_MERCHANT_LISTINGS_ALL_DATA",
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert response["error"] == "auth_failed"
        assert "Failed to get Amazon access token" in response["message"]
        
        # Test AWS credentials failure
        mock_access_token.return_value = "test_access_token"
        mock_aws_creds.return_value = None
        
        result = create_report(
            auth_token=self.test_token,
            report_type="GET_MERCHANT_LISTINGS_ALL_DATA",
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert response["error"] == "auth_failed"
        assert "Failed to get AWS credentials" in response["message"]