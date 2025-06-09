# Makefile for D&D Notetaker
# A comprehensive build system for the D&D session recording processor

# Variables
PYTHON := python3
PIP := pip
VENV := venv
SRC_DIR := src/dnd_notetaker
TEST_DIR := tests
SCRIPTS_DIR := scripts

# Default output directory
OUTPUT_DIR := output

# Python executable in virtual environment
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help setup install dev-install test test-coverage lint format clean clean-all run process list-sessions clean-sessions demo check-deps

# Help target - displays available commands
help:
	@echo "D&D Notetaker - Available Commands:"
	@echo "=================================="
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete setup (venv, deps, ffmpeg check)"
	@echo "  make install        - Install production dependencies"
	@echo "  make dev-install    - Install all dependencies (including test)"
	@echo "  make check-deps     - Check system dependencies (ffmpeg)"
	@echo ""
	@echo "Running the Application:"
	@echo "  make run            - Run full pipeline (alias for 'make process')"
	@echo "  make process        - Process a session recording"
	@echo "  make process-dir DIR=/path/to/dir - Process existing directory"
	@echo "  make process-subject SUBJECT='Meeting Name' - Process by email subject"
	@echo "  make list-sessions  - List temporary directories"
	@echo "  make clean-sessions - Clean old temporary files"
	@echo ""
	@echo "Individual Components:"
	@echo "  make download       - Download recording only"
	@echo "  make extract-audio  - Extract audio from video"
	@echo "  make transcribe     - Generate transcript from audio"
	@echo "  make process-notes  - Process transcript into notes"
	@echo "  make upload-docs    - Upload notes to Google Docs"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run all tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run code linting (pylint)"
	@echo "  make format         - Format code with black"
	@echo "  make demo           - Run demo setup"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean temporary files and cache"
	@echo "  make clean-all      - Clean everything (including venv)"
	@echo ""
	@echo "Configuration:"
	@echo "  make setup-creds    - Interactive credential setup"

# Setup virtual environment and install dependencies
setup: $(VENV)/bin/activate install check-deps
	@echo "✓ Setup complete!"
	@echo "Activate virtual environment with: source $(VENV)/bin/activate"

# Create virtual environment
$(VENV)/bin/activate:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip

# Install production dependencies
install: $(VENV)/bin/activate
	@echo "Installing production dependencies..."
	$(VENV_PIP) install -r requirements.txt

# Install all dependencies (including dev/test)
dev-install: $(VENV)/bin/activate
	@echo "Installing all dependencies..."
	$(VENV_PIP) install -r requirements.txt

# Check system dependencies
check-deps:
	@echo "Checking system dependencies..."
	@command -v ffmpeg >/dev/null 2>&1 && echo "✓ ffmpeg is installed" || \
		(echo "✗ ffmpeg is not installed. Please install it:"; \
		 echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"; \
		 echo "  macOS: brew install ffmpeg"; \
		 echo "  Windows: Download from https://ffmpeg.org/download.html"; \
		 exit 1)

# Run tests
test: $(VENV)/bin/activate
	@echo "Running tests..."
	$(VENV_PYTHON) -m pytest $(TEST_DIR) -v

# Run tests with coverage
test-coverage: $(VENV)/bin/activate
	@echo "Running tests with coverage..."
	$(VENV_PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term

# Lint code
lint: $(VENV)/bin/activate
	@echo "Running linting..."
	$(VENV_PIP) install -q pylint
	$(VENV_PYTHON) -m pylint $(SRC_DIR)

# Format code
format: $(VENV)/bin/activate
	@echo "Formatting code..."
	$(VENV_PIP) install -q black isort
	$(VENV_PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)
	$(VENV_PYTHON) -m black $(SRC_DIR) $(TEST_DIR)

# Clean temporary files and cache
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf temp_download/
	@echo "✓ Cleaned temporary files"

# Clean everything including virtual environment
clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "✓ Cleaned everything"

# Run the main application (full pipeline)
run: process

# Process a session recording (full pipeline)
process: $(VENV)/bin/activate
	@echo "Processing D&D session recording..."
	$(VENV_PYTHON) -m dnd_notetaker.main process $(ARGS)

# Process with specific output directory
process-dir: $(VENV)/bin/activate
	@echo "Processing with directory: $(DIR)"
	$(VENV_PYTHON) -m dnd_notetaker.main process --dir "$(DIR)"

# Process by email subject
process-subject: $(VENV)/bin/activate
	@echo "Processing by email subject: $(SUBJECT)"
	$(VENV_PYTHON) -m dnd_notetaker.main process --subject "$(SUBJECT)"

# List temporary directories
list-sessions: $(VENV)/bin/activate
	@echo "Listing temporary directories..."
	$(VENV_PYTHON) -m dnd_notetaker.main list

# Clean old temporary files
clean-sessions: $(VENV)/bin/activate
	@echo "Cleaning old temporary files..."
	$(VENV_PYTHON) -m dnd_notetaker.main clean

# Individual component targets
download: $(VENV)/bin/activate
	@echo "Downloading recording from email..."
	$(VENV_PYTHON) -m dnd_notetaker.email_handler -o $(OUTPUT_DIR)

extract-audio: $(VENV)/bin/activate
	@echo "Extracting audio from video..."
	@test -n "$(VIDEO)" || (echo "Error: VIDEO variable not set. Use: make extract-audio VIDEO=path/to/video.mp4"; exit 1)
	$(VENV_PYTHON) -m dnd_notetaker.audio_processor -i "$(VIDEO)" -o $(OUTPUT_DIR)

transcribe: $(VENV)/bin/activate
	@echo "Generating transcript..."
	@test -n "$(AUDIO)" || (echo "Error: AUDIO variable not set. Use: make transcribe AUDIO=path/to/audio.mp3"; exit 1)
	$(VENV_PYTHON) -m dnd_notetaker.transcriber -i "$(AUDIO)" -o $(OUTPUT_DIR)

process-notes: $(VENV)/bin/activate
	@echo "Processing transcript into notes..."
	@test -n "$(TRANSCRIPT)" || (echo "Error: TRANSCRIPT variable not set. Use: make process-notes TRANSCRIPT=path/to/transcript.txt"; exit 1)
	$(VENV_PYTHON) -m dnd_notetaker.transcript_processor -i "$(TRANSCRIPT)" -o $(OUTPUT_DIR)

upload-docs: $(VENV)/bin/activate
	@echo "Uploading to Google Docs..."
	@test -n "$(NOTES)" || (echo "Error: NOTES variable not set. Use: make upload-docs NOTES=path/to/notes.txt"; exit 1)
	@test -n "$(TITLE)" || (echo "Error: TITLE variable not set. Use: make upload-docs NOTES=path/to/notes.txt TITLE='Session Title'"; exit 1)
	$(VENV_PYTHON) -m dnd_notetaker.docs_uploader -i "$(NOTES)" -t "$(TITLE)"

# Setup credentials interactively
setup-creds: $(VENV)/bin/activate
	@echo "Setting up credentials..."
	$(VENV_PYTHON) $(SCRIPTS_DIR)/setup_credentials.py

# Run demo setup
demo: $(VENV)/bin/activate
	@echo "Running demo setup..."
	cd $(SCRIPTS_DIR) && bash demo_setup.sh

# Development shortcuts
dev: dev-install test lint

# Quick test for CI/CD
ci: setup test-coverage lint

# Print current configuration
config-info:
	@echo "D&D Notetaker Configuration:"
	@echo "==========================="
	@echo "Python: $(PYTHON)"
	@echo "Virtual Environment: $(VENV)"
	@echo "Source Directory: $(SRC_DIR)"
	@echo "Test Directory: $(TEST_DIR)"
	@echo "Scripts Directory: $(SCRIPTS_DIR)"
	@echo "Output Directory: $(OUTPUT_DIR)"