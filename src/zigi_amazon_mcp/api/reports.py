"""Reports API client for Amazon SP-API bulk operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import requests  # type: ignore[import-untyped]

from ..constants import API_PATHS
from ..exceptions import RateLimitError
from ..utils.validators import (
    validate_iso8601_date,
    validate_marketplace_ids,
)
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class ReportsAPIClient(BaseAPIClient):
    """Client for Amazon SP-API Reports operations (bulk FBM/FBA data)."""

    # Report types for inventory management
    REPORT_TYPES = {
        "ALL_LISTINGS": "GET_MERCHANT_LISTINGS_ALL_DATA",
        "ACTIVE_LISTINGS": "GET_MERCHANT_LISTINGS_DATA",
        "INACTIVE_LISTINGS": "GET_MERCHANT_LISTINGS_INACTIVE_DATA",
        "FBA_INVENTORY": "GET_AFN_INVENTORY_DATA",
        "MERCHANT_LISTINGS": "GET_MERCHANT_LISTINGS_DATA_BACK_COMPAT",
    }

    def get_api_path(self) -> str:
        """Return the base API path for reports operations."""
        return API_PATHS["reports"]

    def create_report(
        self,
        report_type: str,
        marketplace_ids: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a new report request.

        Args:
            report_type: Type of report to create
            marketplace_ids: Comma-separated marketplace IDs
            start_date: ISO 8601 format start date
            end_date: ISO 8601 format end date
            report_options: Additional report-specific options

        Returns:
            Dict containing the formatted response with report ID
        """
        try:
            # Validate inputs
            validation_errors = []

            if report_type not in self.REPORT_TYPES.values():
                validation_errors.append(f"Invalid report_type. Valid types: {', '.join(self.REPORT_TYPES.values())}")

            is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
            if not is_valid_marketplace:
                validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")

            if start_date and not validate_iso8601_date(start_date):
                validation_errors.append(f"Invalid start_date format: {start_date}")

            if end_date and not validate_iso8601_date(end_date):
                validation_errors.append(f"Invalid end_date format: {end_date}")

            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Build request body
            body: dict[str, Any] = {
                "reportType": report_type,
                "marketplaceIds": marketplace_ids.split(","),
            }

            if start_date:
                body["dataStartTime"] = start_date
            if end_date:
                body["dataEndTime"] = end_date
            if report_options:
                body["reportOptions"] = report_options

            # Make API request
            result = self._make_request("POST", self.get_api_path(), data=body)

            # Extract report ID
            report_id = result.get("reportId", "")

            return self._format_success_response(
                {
                    "reportId": report_id,
                    "reportType": report_type,
                    "status": "IN_QUEUE",
                    "createdTime": datetime.now(timezone.utc).isoformat(),
                },
                metadata={
                    "marketplace": marketplace_ids.split(",")[0],
                    "report_type": report_type,
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
            logger.exception(f"Unexpected error in create_report: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def get_report(self, report_id: str) -> dict[str, Any]:
        """Get the status and details of a report.

        Args:
            report_id: The report ID to check

        Returns:
            Dict containing the report status and details
        """
        try:
            if not report_id:
                return self._format_error_response(
                    "invalid_input",
                    "report_id is required",
                )

            # Build request path
            path = f"{self.get_api_path()}/{report_id}"

            # Make API request
            result = self._make_request("GET", path)

            # Transform response
            report_data = self._transform_report_response(result)

            return self._format_success_response(
                report_data,
                metadata={
                    "report_id": report_id,
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
            logger.exception(f"Unexpected error in get_report: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def get_report_document(self, report_document_id: str) -> dict[str, Any]:
        """Get the download URL for a report document.

        Args:
            report_document_id: The report document ID

        Returns:
            Dict containing the document URL and compression details
        """
        try:
            if not report_document_id:
                return self._format_error_response(
                    "invalid_input",
                    "report_document_id is required",
                )

            # Build request path
            path = f"/reports/2021-06-30/documents/{report_document_id}"

            # Make API request
            result = self._make_request("GET", path)

            return self._format_success_response(
                {
                    "url": result.get("url"),
                    "compressionAlgorithm": result.get("compressionAlgorithm"),
                    "reportDocumentId": report_document_id,
                },
                metadata={
                    "report_document_id": report_document_id,
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
            logger.exception(f"Unexpected error in get_report_document: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def get_reports(
        self,
        report_types: Optional[list[str]] = None,
        processing_statuses: Optional[list[str]] = None,
        marketplace_ids: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get a list of reports matching the criteria.

        Args:
            report_types: List of report types to filter by
            processing_statuses: List of processing statuses to filter by
            marketplace_ids: Comma-separated marketplace IDs
            created_after: ISO 8601 format date
            created_before: ISO 8601 format date
            max_results: Maximum number of results

        Returns:
            Dict containing the list of reports
        """
        try:
            # Validate inputs
            validation_errors = []

            if marketplace_ids:
                is_valid_marketplace, invalid_ids = validate_marketplace_ids(marketplace_ids)
                if not is_valid_marketplace:
                    validation_errors.append(f"Invalid marketplace IDs: {', '.join(invalid_ids)}")

            if created_after and not validate_iso8601_date(created_after):
                validation_errors.append(f"Invalid created_after format: {created_after}")

            if created_before and not validate_iso8601_date(created_before):
                validation_errors.append(f"Invalid created_before format: {created_before}")

            if validation_errors:
                return self._format_error_response(
                    "invalid_input",
                    "Input validation failed",
                    details=validation_errors,
                )

            # Build query parameters
            params: dict[str, Any] = {"maxResults": min(max_results, 100)}

            if report_types:
                params["reportTypes"] = ",".join(report_types)
            if processing_statuses:
                params["processingStatuses"] = ",".join(processing_statuses)
            if marketplace_ids:
                params["marketplaceIds"] = marketplace_ids
            if created_after:
                params["createdSince"] = created_after
            if created_before:
                params["createdUntil"] = created_before

            # Make API request
            result = self._make_request("GET", self.get_api_path(), params=params)

            # Transform reports list
            reports = result.get("reports", [])
            transformed_reports = [self._transform_report_response(report) for report in reports]

            return self._format_success_response(
                {
                    "reports": transformed_reports,
                    "count": len(transformed_reports),
                },
                metadata={
                    "filters_applied": bool(report_types or processing_statuses or marketplace_ids),
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
            logger.exception(f"Unexpected error in get_reports: {e}")
            return self._format_error_response(
                "unexpected_error",
                f"An unexpected error occurred: {e!s}",
            )

    def _transform_report_response(self, report: dict[str, Any]) -> dict[str, Any]:
        """Transform raw report response to consistent format.

        Args:
            report: Raw report data from API

        Returns:
            Transformed report data
        """
        return {
            "reportId": report.get("reportId"),
            "reportType": report.get("reportType"),
            "marketplaceIds": report.get("marketplaceIds", []),
            "processingStatus": report.get("processingStatus"),
            "createdTime": report.get("createdTime"),
            "processingStartTime": report.get("processingStartTime"),
            "processingEndTime": report.get("processingEndTime"),
            "reportDocumentId": report.get("reportDocumentId"),
            "dataStartTime": report.get("dataStartTime"),
            "dataEndTime": report.get("dataEndTime"),
        }

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
            message = "Report not found."
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
