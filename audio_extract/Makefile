# Makefile for audio_extract module
# Makes development and testing easier with organized commands

# Virtual environment settings
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Check if we're already in a venv
IN_VENV := $(shell python -c "import sys; print('1' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else '0')")

ifeq ($(IN_VENV),1)
    # Already in a virtual environment, use current Python
    PYTHON := python
    PIP := pip
endif

.PHONY: help install test clean docker run dev prod health lint format check-deps setup-dev venv check-test-deps check-lint-deps check-format-deps check-type-deps

# Default target - show help
help:
	@echo "Audio Extract Module - Development Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install dev dependencies"
	@echo "  make setup-dev    - Complete development setup"
	@echo "  make check-deps   - Check system dependencies (ffmpeg, etc)"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-storage - Run storage tests"
	@echo "  make test-cli     - Run CLI tests"
	@echo "  make coverage     - Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make run          - Run monitor in dev mode (no health check)"
	@echo "  make run-once     - Run single check cycle"
	@echo "  make run-with-health - Run monitor with health check endpoint"
	@echo "  make test-connection - Test Drive connection"
	@echo "  make dashboard    - Run dashboard only"
	@echo "  make extract      - Extract audio from a video file"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run in Docker (dev mode)"
	@echo "  make docker-prod  - Run in Docker (prod mode)"
	@echo "  make docker-shell - Shell into container"
	@echo "  make docker-logs  - View container logs"
	@echo "  make docker-stop  - Stop all containers"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black"
	@echo "  make type-check   - Run type checking"
	@echo "  Note: Run 'make install-dev' first for linting/formatting"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean        - Clean temporary files"
	@echo "  make clean-all    - Clean everything including venv"
	@echo "  make db-reset     - Reset tracking database"
	@echo "  make example      - Run storage example"
	@echo "  make activate     - Show venv activation instructions"
	@echo ""
	@echo "Note: All Python commands automatically use the virtual environment."
	@echo "      The venv is created at ./$(VENV) on first use."
	@echo ""

# Virtual Environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		echo "Virtual environment created at $(VENV)"; \
	fi

# Setup & Installation
install: venv
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt

setup-dev: install-dev
	@echo "Setting up development environment..."
	@echo "Creating directories..."
	mkdir -p data logs output output/dev output/temp .credentials
	@echo "Checking system dependencies..."
	@make check-deps
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Add your service account JSON to .credentials/"
	@echo "2. Update audio_extract_config.dev.yaml with your folder ID"
	@echo "3. Run 'make test-connection' to verify setup"
	@echo ""
	@echo "Note: Virtual environment created at ./$(VENV)"
	@echo "All Python commands will use this environment automatically."

check-deps:
	@echo "Checking system dependencies..."
	@command -v ffmpeg >/dev/null 2>&1 && echo "✓ FFmpeg installed" || echo "✗ FFmpeg NOT FOUND - install with: apt install ffmpeg"
	@command -v python3 >/dev/null 2>&1 && echo "✓ Python3 installed" || echo "✗ Python3 NOT FOUND"
	@command -v docker >/dev/null 2>&1 && echo "✓ Docker installed" || echo "✗ Docker not installed (optional)"
	@$(PYTHON) -c "import yaml" 2>/dev/null && echo "✓ PyYAML installed" || echo "✗ PyYAML not installed"

# Testing (requires install-dev)
test: venv check-test-deps
	@echo "Running all tests..."
	$(PYTHON) -m pytest tests/ -v

test-unit: venv check-test-deps
	@echo "Running unit tests..."
	$(PYTHON) -m pytest tests/test_*.py -v -k "not integration"

test-integration: venv check-test-deps
	@echo "Running integration tests..."
	$(PYTHON) -m pytest tests/test_*integration*.py -v

test-storage: venv check-test-deps
	@echo "Running storage tests..."
	$(PYTHON) -m pytest tests/test_storage*.py -v

test-cli: venv check-test-deps
	@echo "Running CLI tests..."
	$(PYTHON) -m pytest tests/test_cli_monitor.py -v

coverage: venv check-test-deps
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=audio_extract --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

# Check if test dependencies are installed
check-test-deps:
	@$(PYTHON) -c "import pytest" 2>/dev/null || (echo "Error: pytest not installed. Run 'make install-dev' first." && exit 1)

# Development Commands
run: venv
	@echo "Starting audio extract monitor (dev mode)..."
	$(PYTHON) -m audio_extract.cli.monitor --config audio_extract_config.dev.yaml --no-health-check

run-once: venv
	@echo "Running single check cycle..."
	$(PYTHON) -m audio_extract.cli.monitor --config audio_extract_config.dev.yaml --once --no-health-check

run-with-health: venv
	@echo "Starting audio extract monitor with health check endpoint..."
	$(PYTHON) -m audio_extract.cli.monitor --config audio_extract_config.dev.yaml

test-connection: venv
	@echo "Testing Google Drive connection..."
	$(PYTHON) -m audio_extract.cli.monitor --config audio_extract_config.dev.yaml --test

dashboard: venv
	@echo "Starting dashboard server..."
	$(PYTHON) -m audio_extract.dashboard.server

extract: venv
	@if [ -z "$(VIDEO)" ]; then \
		echo "Usage: make extract VIDEO=path/to/video.mp4"; \
		exit 1; \
	fi
	@echo "Extracting audio from $(VIDEO)..."
	$(PYTHON) -m audio_extract.extractor "$(VIDEO)" output/

# Docker Commands
docker-build:
	@echo "Building Docker image..."
	docker build -t audio-extract .

docker-run: docker-build
	@echo "Running in Docker (dev mode)..."
	docker-compose up

docker-prod:
	@echo "Running in Docker (production mode)..."
	docker-compose -f docker-compose.prod.yml up -d

docker-shell:
	@echo "Opening shell in container..."
	docker-compose run --rm audio-extract /bin/bash

docker-logs:
	@echo "Viewing container logs..."
	docker-compose logs -f --tail=100

docker-stop:
	@echo "Stopping containers..."
	docker-compose down
	docker-compose -f docker-compose.prod.yml down

# Code Quality (requires install-dev)
lint: venv check-lint-deps
	@echo "Running linting checks..."
	@echo "Python linting..."
	$(PYTHON) -m flake8 . --max-line-length=100 --exclude=__pycache__,venv
	@echo "YAML linting..."
	$(PYTHON) -m yamllint audio_extract_config.*.yaml || true

format: venv check-format-deps
	@echo "Formatting code with black..."
	$(PYTHON) -m black . --line-length=100 --exclude venv/

type-check: venv check-type-deps
	@echo "Running type checking..."
	$(PYTHON) -m mypy --config-file mypy.ini . || true

# Check linting dependencies
check-lint-deps:
	@$(PYTHON) -c "import flake8" 2>/dev/null || (echo "Error: flake8 not installed. Run 'make install-dev' first." && exit 1)

check-format-deps:
	@$(PYTHON) -c "import black" 2>/dev/null || (echo "Error: black not installed. Run 'make install-dev' first." && exit 1)

check-type-deps:
	@$(PYTHON) -c "import mypy" 2>/dev/null || (echo "Error: mypy not installed. Run 'make install-dev' first." && exit 1)

# Utilities
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/
	@echo "Cleaned!"
	@echo "Note: Virtual environment preserved. Use 'make clean-all' to remove it."

db-reset:
	@echo "Resetting tracking database..."
	@read -p "Are you sure? This will delete all processing history [y/N]: " confirm && \
	if [ "$$confirm" = "y" ]; then \
		rm -f data/dev/processed.db data/prod/processed.db; \
		echo "Database reset!"; \
	else \
		echo "Cancelled."; \
	fi

example: venv
	@echo "Running storage example..."
	$(PYTHON) audio_extract/examples/storage_example.py

# Health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8081/health | $(PYTHON) -m json.tool || echo "Health service not running"

# Production helpers
prod: venv
	@echo "Starting in production mode..."
	$(PYTHON) -m audio_extract.cli.monitor --config audio_extract_config.prod.yaml

prod-status:
	@echo "Checking production status..."
	@if systemctl is-active --quiet audio-extract; then \
		echo "✓ Service is running"; \
		systemctl status audio-extract --no-pager | head -10; \
	else \
		echo "✗ Service is not running"; \
	fi

# Development shortcuts
dev: run

status: venv
	@echo "Recent processing status..."
	$(PYTHON) -m audio_extract.tracker --status --recent 10

# Quick test commands
test-quick: venv
	@echo "Running quick smoke tests..."
	$(PYTHON) -m pytest tests/test_utils.py tests/test_exceptions.py -v

# Install development dependencies
install-dev: venv
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "Development dependencies installed!"

# Environment setup helpers
setup-gcs:
	@echo "GCS Setup Instructions:"
	@echo "======================"
	@echo "1. Install gcsfuse:"
	@echo "   Ubuntu: sudo apt-get install gcsfuse"
	@echo "   macOS: brew install --cask macfuse && brew install gcsfuse"
	@echo ""
	@echo "2. Create mount directory:"
	@echo "   mkdir -p ~/audio-extracts-mount"
	@echo ""
	@echo "3. Mount your bucket:"
	@echo "   gcsfuse --implicit-dirs YOUR-BUCKET ~/audio-extracts-mount"
	@echo ""
	@echo "4. Update config to use mount:"
	@echo "   storage:"
	@echo "     type: local"
	@echo "     local:"
	@echo "       path: ~/audio-extracts-mount/audio"

# Configuration validation
validate-config: venv
	@echo "Validating configuration files..."
	@$(PYTHON) -c "import yaml; yaml.safe_load(open('audio_extract_config.dev.yaml'))" && echo "✓ Dev config valid" || echo "✗ Dev config invalid"
	@$(PYTHON) -c "import yaml; yaml.safe_load(open('audio_extract_config.prod.yaml'))" && echo "✓ Prod config valid" || echo "✗ Prod config invalid"

# Show current configuration
show-config: venv
	@echo "Current configuration (dev):"
	@$(PYTHON) -c "import yaml, json; print(json.dumps(yaml.safe_load(open('audio_extract_config.dev.yaml')), indent=2))"

# Activate virtual environment instructions
activate:
	@echo "To activate the virtual environment manually:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "Note: Make commands automatically use the venv."

# Clean virtual environment
clean-venv:
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Virtual environment removed."

# Full clean including venv
clean-all: clean clean-venv
	@echo "All cleaned!"