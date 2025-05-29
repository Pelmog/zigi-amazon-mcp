#!/bin/bash
# MCP Inspector Utility Script for zigi-amazon-mcp
# This script helps test and debug the MCP server endpoints

set -euo pipefail

# Configuration
SERVER_PACKAGE="zigi-amazon-mcp"
SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                          MCP Inspector Utility                              ║"
    echo "║                          zigi-amazon-mcp Server                             ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "${YELLOW}━━━ $1 ━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_requirements() {
    print_section "Checking Requirements"

    # Check if npx is available
    if ! command -v npx &> /dev/null; then
        print_error "npx is not installed. Please install Node.js and npm first."
        exit 1
    fi
    print_success "npx is available"

    # Check if uv is available
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install uv first."
        echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_success "uv is available"

    # Check if server package exists
    if [ ! -f "$SERVER_DIR/pyproject.toml" ]; then
        print_error "pyproject.toml not found in $SERVER_DIR"
        exit 1
    fi
    print_success "Project structure is valid"

    echo
}

show_usage() {
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  inspect     Launch MCP Inspector (default)"
    echo "  test        Run automated tests (not yet implemented)"
    echo "  env-check   Check environment variables"
    echo "  info        Show server information"
    echo "  help        Show this help message"
    echo
}

load_env_file() {
    # Load .env file if it exists
    if [ -f "$SERVER_DIR/.env" ]; then
        # Export variables from .env file
        set -a
        source "$SERVER_DIR/.env"
        set +a
        print_success ".env file loaded"
    else
        print_info "No .env file found in $SERVER_DIR"
    fi
}

check_env_vars() {
    print_section "Environment Variables Check"

    # Load .env file first
    load_env_file

    local env_vars=("LWA_CLIENT_ID" "LWA_CLIENT_SECRET" "LWA_REFRESH_TOKEN" "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY")
    local missing_vars=()

    for var in "${env_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
            print_error "$var is not set"
        else
            print_success "$var is set"
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_info "Missing environment variables. Some Amazon SP-API functions may not work."
        print_info "Create a .env file in the project root with these variables:"
        for var in "${missing_vars[@]}"; do
            echo "  $var=your_value_here"
        done
        echo
        print_info "Or set them in your shell:"
        for var in "${missing_vars[@]}"; do
            echo "  export $var=\"your_value_here\""
        done
    fi

    echo
}

launch_inspector() {
    print_section "Launching MCP Inspector"

    print_info "Starting MCP Inspector for $SERVER_PACKAGE..."
    print_info "The Inspector will open in your default web browser"
    print_info "Press Ctrl+C to stop the inspector"
    echo

    # Change to server directory and launch inspector
    cd "$SERVER_DIR"

    # Use npx to launch inspector with uv run
    npx @modelcontextprotocol/inspector \
        uv \
        --directory "$SERVER_DIR" \
        run \
        "$SERVER_PACKAGE"
}

run_automated_tests() {
    print_section "Running Automated MCP Tests"

    print_info "This would run automated tests against the MCP server"
    print_info "Tests would include:"
    echo "  - Connection establishment"
    echo "  - Authentication flow"
    echo "  - All tool endpoints"
    echo "  - Error handling"
    echo "  - Session management"
    echo
    print_info "Automated testing not yet implemented."
    print_info "Use 'inspect' mode to manually test endpoints in the GUI."
}

show_server_info() {
    print_section "Server Information"

    print_info "Server Package: $SERVER_PACKAGE"
    print_info "Server Directory: $SERVER_DIR"
    print_info "Main Module: src/zigi_amazon_mcp/server.py"
    echo
    print_info "Available MCP Tools:"
    echo "  1. get_auth_token - Generate authentication token (call first!)"
    echo "  2. hello_world - Simple greeting tool"
    echo "  3. process_text - Text processing operations"
    echo "  4. read_file - Read local file contents"
    echo "  5. write_file - Write content to local files"
    echo "  6. json_process - Parse/format JSON data"
    echo "  7. convert_data - Convert between data formats"
    echo "  8. store_session_data - Store data by session ID"
    echo "  9. get_session_data - Retrieve stored session data"
    echo "  10. get_orders - Retrieve Amazon orders (requires credentials)"
    echo "  11. get_order - Retrieve single Amazon order (requires credentials)"
    echo
    print_info "IMPORTANT: Call get_auth_token first to obtain authentication token!"
    print_info "All other functions require the auth_token parameter."
    echo
}

main() {
    print_header

    # Parse command line arguments
    case "${1:-inspect}" in
        "inspect")
            check_requirements
            show_server_info
            check_env_vars
            launch_inspector
            ;;
        "test")
            check_requirements
            run_automated_tests
            ;;
        "env-check")
            check_env_vars
            ;;
        "info")
            show_server_info
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
