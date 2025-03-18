.PHONY: install format lint type-check test clean

# Default Python executable
PYTHON = python

# Directory containing source code
SRC_DIR = mcp_server_podcast
TEST_DIR = tests

# Default target executed when no arguments are given to make.
default: help

# Install the package in development mode
install:
	uv sync
	uv pip install -e .

# Format the code with ruff
format:
	ruff format $(SRC_DIR) $(TEST_DIR)

# Run ruff linter
lint:
	ruff check $(SRC_DIR) $(TEST_DIR)

# Run pyright type checker
type-check:
	pyright $(SRC_DIR)

# Run tests with pytest
test:
	pytest $(TEST_DIR)

# Run a specific test file or function
test-file:
	pytest $(filter-out $@,$(MAKECMDGOALS)) -v

# Run the MCP server in stdio mode
run:
	uv run mcp-server-podcast

# Run the MCP server in SSE mode
run-sse:
	uv run mcp-server-podcast --transport sse --port 6090

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Display help information
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install     Install the package in development mode"
	@echo "  format      Format the code with ruff"
	@echo "  lint        Run ruff linter"
	@echo "  type-check  Run pyright type checker"
	@echo "  test        Run tests with pytest"
	@echo "  test-file   Run a specific test file (e.g., make test-file tests/test_server.py)"
	@echo "  run         Run the MCP server in stdio mode"
	@echo "  run-sse     Run the MCP server in SSE mode (port 6090)"
	@echo "  clean       Remove build artifacts"
	@echo "  help        Show this help message"

# Catch non-target arguments (for test-file)
%:
	@: