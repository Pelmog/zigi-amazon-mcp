# MCP Server Endpoints Documentation

The Zigi Amazon MCP server provides 6 tools for various data processing and I/O operations.

## Available Tools

### 1. hello_world
Simple greeting tool that returns a personalized message.

**Parameters:**
- `name` (string, optional): Name to greet. Defaults to "World"

**Example:**
```json
{
  "tool": "hello_world",
  "arguments": {
    "name": "Alice"
  }
}
```

**Response:**
```
Hello, Alice! This is the Zigi Amazon MCP server.
```

### 2. process_text
Process text with various string operations.

**Parameters:**
- `text` (string, required): The text to process
- `operation` (string, required): Operation to perform
  - `uppercase`: Convert to uppercase
  - `lowercase`: Convert to lowercase
  - `reverse`: Reverse the text
  - `count_words`: Count number of words
  - `count_chars`: Count number of characters

**Example:**
```json
{
  "tool": "process_text",
  "arguments": {
    "text": "Hello World",
    "operation": "uppercase"
  }
}
```

**Response:**
```
HELLO WORLD
```

### 3. read_file
Read content from a local file.

**Parameters:**
- `file_path` (string, required): Path to the file to read
- `encoding` (string, optional): File encoding. Defaults to "utf-8"

**Example:**
```json
{
  "tool": "read_file",
  "arguments": {
    "file_path": "/path/to/file.txt"
  }
}
```

### 4. write_file
Write content to a local file.

**Parameters:**
- `file_path` (string, required): Path to the file to write
- `content` (string, required): Content to write
- `encoding` (string, optional): File encoding. Defaults to "utf-8"
- `append` (boolean, optional): Append instead of overwrite. Defaults to false

**Example:**
```json
{
  "tool": "write_file",
  "arguments": {
    "file_path": "/tmp/output.txt",
    "content": "Hello from MCP!",
    "append": false
  }
}
```

### 5. json_process
Parse, format, or validate JSON data.

**Parameters:**
- `data` (string, required): JSON string or object
- `operation` (string, required): Operation to perform
  - `parse`: Parse JSON string to object
  - `format`: Format object as pretty JSON
  - `validate`: Check if JSON is valid
- `indent` (number, optional): Indentation for formatting. Defaults to 2

**Example:**
```json
{
  "tool": "json_process",
  "arguments": {
    "data": "{\"name\": \"test\", \"value\": 42}",
    "operation": "format",
    "indent": 4
  }
}
```

### 6. convert_data
Convert data between different formats.

**Parameters:**
- `data` (string, required): Data to convert
- `from_format` (string, required): Source format
  - `text`: Plain text
  - `base64`: Base64 encoded
  - `hex`: Hexadecimal
- `to_format` (string, required): Target format
  - `text`: Plain text
  - `base64`: Base64 encoded
  - `hex`: Hexadecimal

**Example:**
```json
{
  "tool": "convert_data",
  "arguments": {
    "data": "Hello",
    "from_format": "text",
    "to_format": "base64"
  }
}
```

**Response:**
```
SGVsbG8=
```

## Error Handling

All tools return errors in a consistent format:
- Unknown tool: `"Error: Unknown tool: {tool_name}"`
- Invalid parameters: `"Error: {specific_error_message}"`
- File operations: `"Error reading/writing file: {error_details}"`
- JSON operations: `"Error processing JSON: {error_details}"`
- Data conversion: `"Error converting data: {error_details}"`

## Usage with MCP

These tools are exposed through the Model Context Protocol (MCP) and can be accessed by any MCP-compatible client. The server uses stdio for communication and supports async operations.