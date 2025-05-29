"""Tests for the MCP server."""

import base64
import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from zigi_amazon_mcp.server import (
    convert_data,
    hello_world,
    json_process,
    process_text,
    read_file,
    write_file,
)


def test_hello_world():
    """Test the hello_world tool."""
    # Test with default name
    result = hello_world()
    assert "Hello, World!" in result
    assert "Zigi Amazon MCP server" in result

    # Test with custom name
    result = hello_world("Alice")
    assert "Hello, Alice!" in result


def test_process_text():
    """Test the process_text tool with various operations."""
    test_text = "Hello World"

    # Test uppercase
    result = process_text(test_text, "uppercase")
    assert result == "HELLO WORLD"

    # Test lowercase
    result = process_text(test_text, "lowercase")
    assert result == "hello world"

    # Test reverse
    result = process_text(test_text, "reverse")
    assert result == "dlroW olleH"

    # Test count_words
    result = process_text(test_text, "count_words")
    assert result == "2"

    # Test count_chars
    result = process_text(test_text, "count_chars")
    assert result == "11"

    # Test invalid operation
    with pytest.raises(ValueError) as exc_info:
        process_text(test_text, "invalid")
    assert "Invalid operation: invalid" in str(exc_info.value)


def test_read_file():
    """Test the read_file tool."""
    # Test successful read
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.read_text", return_value="File content"),
    ):
        result = read_file("/tmp/test.txt")
        assert result == "File content"

    # Test non-existent file
    with patch("pathlib.Path.exists", return_value=False):
        result = read_file("/tmp/nonexistent.txt")
        assert "Error reading file: File not found" in result

    # Test directory instead of file
    with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_file", return_value=False):
        result = read_file("/tmp")
        assert "Error reading file: Path is not a file" in result


def test_write_file():
    """Test the write_file tool."""
    # Test successful write
    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text") as mock_write:
        result = write_file("/tmp/test.txt", "Test content")
        assert "Successfully wrote to /tmp/test.txt" in result
        mock_write.assert_called_once_with("Test content", encoding="utf-8")

    # Test append mode
    with patch("pathlib.Path.mkdir"), patch("builtins.open", mock_open()) as mock_file:
        result = write_file("/tmp/test.txt", "Appended content", append=True)
        assert "Successfully wrote to /tmp/test.txt" in result
        mock_file.assert_called_once_with(Path("/tmp/test.txt"), "a", encoding="utf-8")

    # Test write error
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission")):
        result = write_file("/root/test.txt", "Test")
        assert "Error writing file: No permission" in result


def test_json_process():
    """Test the json_process tool."""
    # Test parse
    json_str = '{"name": "test", "value": 42}'
    result = json_process(json_str, "parse")
    assert "Parsed JSON: {'name': 'test', 'value': 42}" in result

    # Test format
    result = json_process(json_str, "format", indent=2)
    parsed = json.loads(result)
    assert parsed["name"] == "test"
    assert parsed["value"] == 42

    # Test validate - valid JSON
    result = json_process(json_str, "validate")
    assert result == "Valid JSON"

    # Test validate - invalid JSON
    result = json_process("{invalid}", "validate")
    assert "Invalid JSON:" in result

    # Test invalid operation
    with pytest.raises(ValueError) as exc_info:
        json_process(json_str, "invalid")
    assert "Invalid operation: invalid" in str(exc_info.value)


def test_convert_data():
    """Test the convert_data tool."""
    # Test text to base64
    result = convert_data("Hello", "text", "base64")
    assert result == base64.b64encode(b"Hello").decode("ascii")

    # Test base64 to text
    b64_data = base64.b64encode(b"Hello").decode("ascii")
    result = convert_data(b64_data, "base64", "text")
    assert result == "Hello"

    # Test text to hex
    result = convert_data("Hello", "text", "hex")
    assert result == b"Hello".hex()

    # Test hex to text
    hex_data = b"Hello".hex()
    result = convert_data(hex_data, "hex", "text")
    assert result == "Hello"

    # Test invalid base64
    result = convert_data("invalid!", "base64", "text")
    assert "Error converting data:" in result

    # Test invalid format
    result = convert_data("test", "invalid", "text")
    assert "Error converting data: Invalid source format: invalid" in result
