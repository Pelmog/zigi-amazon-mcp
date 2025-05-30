"""Tests for the MCP server authentication."""

import pytest

from zigi_amazon_mcp.server import (
    get_auth_token,
    validate_auth_token,
    auth_tokens,
)


def test_get_auth_token():
    """Test the get_auth_token function."""
    # Clear any existing tokens
    auth_tokens.clear()
    
    # Get a new token
    result = get_auth_token()
    assert "Authentication successful. Your auth token is:" in result
    
    # Extract the token from the result
    token = result.split(": ")[-1]
    
    # Verify the token is 64 characters (32 bytes in hex)
    assert len(token) == 64
    
    # Verify the token is in the auth_tokens set
    assert token in auth_tokens
    
    # Get another token and verify it's different
    result2 = get_auth_token()
    token2 = result2.split(": ")[-1]
    assert token != token2
    assert token2 in auth_tokens


def test_validate_auth_token():
    """Test the validate_auth_token function."""
    # Clear any existing tokens
    auth_tokens.clear()
    
    # Test with invalid token
    assert validate_auth_token("invalid_token") is False
    
    # Get a valid token
    result = get_auth_token()
    token = result.split(": ")[-1]
    
    # Test with valid token
    assert validate_auth_token(token) is True
    
    # Clear tokens and verify validation fails
    auth_tokens.clear()
    assert validate_auth_token(token) is False