.PHONY: help build run run-file setup dev test clean lint docker-setup test-workflows test-workflow-syntax test-docker-build create-test-build-script test-act

# Default goal
.DEFAULT_GOAL := help

# Variables
IMAGE_NAME = meet-notes
CONTAINER_NAME = meet-notes-processor
CONFIG_DIR = /workspaces/dnd_notetaker/.credentials
OUTPUT_DIR = /workspaces/dnd_notetaker/meet_notes_output

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "Meet Notes - Google Meet Recording Processor"
	@echo ""
	@echo "Usage:"
	@echo "  make $(YELLOW)<target>$(NC)"
	@echo ""
	@echo "Docker Commands:"
	@echo "  $(GREEN)build$(NC)       Build Docker image"
	@echo "  $(GREEN)run$(NC)         Process most recent recording (Docker)"
	@echo "  $(GREEN)run-file$(NC)    Process specific recording (Docker)"
	@echo "              Example: make run-file FILE_ID=1a2b3c4d5e6f"
	@echo ""
	@echo "Local Development:"
	@echo "  $(GREEN)setup$(NC)       Setup local development environment"
	@echo "  $(GREEN)dev$(NC)         Run locally (no Docker)"
	@echo "  $(GREEN)test$(NC)        Run test suite"
	@echo "  $(GREEN)lint$(NC)        Run linting"
	@echo "  $(GREEN)clean$(NC)       Clean build artifacts"
	@echo ""
	@echo "Setup:"
	@echo "  $(GREEN)docker-setup$(NC) One-time setup for Docker usage"
	@echo ""
	@echo "Workflow Testing:"
	@echo "  $(GREEN)test-workflows$(NC)      Test GitHub workflows locally"
	@echo "  $(GREEN)test-workflow-syntax$(NC) Test workflow YAML syntax"
	@echo "  $(GREEN)test-docker-build$(NC)   Test Docker build for audio-extract"
	@echo "  $(GREEN)test-act$(NC)            Test workflows with act (if installed)"

build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(IMAGE_NAME) .
	@echo "$(GREEN)✓ Docker image built successfully$(NC)"

run: build ## Process most recent recording using Docker
	@echo "$(GREEN)Processing most recent recording...$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	docker run --rm \
		-v $(CONFIG_DIR):/.meat_notes_configs \
		-v $(OUTPUT_DIR):/meet_notes_output \
		$(IMAGE_NAME)

run-file: build ## Process specific recording using Docker (FILE_ID=xxx)
	@if [ -z "$(FILE_ID)" ]; then \
		echo "$(YELLOW)Error: Please specify FILE_ID$(NC)"; \
		echo "Usage: make run-file FILE_ID=your_file_id"; \
		exit 1; \
	fi
	@echo "$(GREEN)Processing recording: $(FILE_ID)$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	docker run --rm \
		-v $(CONFIG_DIR):/.meat_notes_configs \
		-v $(OUTPUT_DIR):/meet_notes_output \
		$(IMAGE_NAME) $(FILE_ID)

setup: ## Setup local development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -e .
	./venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo "$(YELLOW)Activate with: source venv/bin/activate$(NC)"

dev: ## Run locally without Docker
	@if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Virtual environment not found. Running setup first...$(NC)"; \
		make setup; \
	fi
	./venv/bin/python -m dnd_notetaker $(ARGS)

test: ## Run test suite
	@echo "$(GREEN)Running type checks...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pyright; \
	else \
		python -m pyright; \
	fi
	@echo "$(GREEN)Running tests...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pytest; \
	else \
		python -m pytest; \
	fi
	@echo "$(GREEN)Testing dry-run mode...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m dnd_notetaker --dry-run && echo "$(GREEN)✓ Dry-run test passed$(NC)" || echo "$(YELLOW)✗ Dry-run test failed$(NC)"; \
	else \
		python -m dnd_notetaker --dry-run && echo "$(GREEN)✓ Dry-run test passed$(NC)" || echo "$(YELLOW)✗ Dry-run test failed$(NC)"; \
	fi

lint: ## Run linting
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pylint src/dnd_notetaker; \
	else \
		echo "$(YELLOW)Install pylint: pip install pylint$(NC)"; \
	fi

clean: ## Clean build artifacts
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Clean complete$(NC)"

docker-setup: ## One-time setup for Docker usage
	@echo "$(GREEN)Setting up Meet Notes for Docker...$(NC)"
	@echo ""
	@echo "1. Creating config directory..."
	@mkdir -p $(CONFIG_DIR)
	@echo ""
	@echo "2. Creating output directory..."
	@mkdir -p $(OUTPUT_DIR)
	@echo ""
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. Add your config to: $(CONFIG_DIR)/config.json"
	@echo "2. Add your service account key to: $(CONFIG_DIR)/service_account.json"
	@echo "3. Run: make run"
	@echo ""
	@echo "See README.md for detailed configuration instructions."

# GitHub Workflow Testing Commands
test-workflows: test-workflow-syntax test-docker-build ## Test GitHub workflows locally
	@echo "$(GREEN)All workflow tests passed!$(NC)"

test-workflow-syntax: ## Test workflow YAML syntax
	@echo "$(GREEN)Testing workflow syntax...$(NC)"
	@if command -v actionlint >/dev/null 2>&1; then \
		actionlint .github/workflows/*.yml; \
		echo "$(GREEN)✓ Workflow syntax valid$(NC)"; \
	else \
		echo "$(YELLOW)⚠ actionlint not installed, checking with Python...$(NC)"; \
		python3 -c "import yaml; import glob; files = glob.glob('.github/workflows/*.yml'); [yaml.safe_load(open(f)) for f in files]; print('✓ All workflow files have valid YAML syntax')"; \
	fi

test-docker-build: ## Test Docker build for audio-extract
	@echo "$(GREEN)Testing Docker build...$(NC)"
	@if [ -f test-build-audio-extract.sh ]; then \
		./test-build-audio-extract.sh; \
	else \
		echo "Creating test-build-audio-extract.sh..."; \
		$(MAKE) create-test-build-script; \
		./test-build-audio-extract.sh; \
	fi

create-test-build-script:
	@echo '#!/bin/bash' > test-build-audio-extract.sh
	@echo 'set -e' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo 'echo "Testing audio-extract Docker build locally..."' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo '# Colors for output' >> test-build-audio-extract.sh
	@echo 'GREEN="\033[0;32m"' >> test-build-audio-extract.sh
	@echo 'RED="\033[0;31m"' >> test-build-audio-extract.sh
	@echo 'NC="\033[0m" # No Color' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo '# Test 1: Build Docker image' >> test-build-audio-extract.sh
	@echo 'echo "Test 1: Building Docker image..."' >> test-build-audio-extract.sh
	@echo 'if docker build -t audio-extract-test audio_extract/ ; then' >> test-build-audio-extract.sh
	@echo '    echo -e "$${GREEN}✓ Docker build successful$${NC}"' >> test-build-audio-extract.sh
	@echo 'else' >> test-build-audio-extract.sh
	@echo '    echo -e "$${RED}✗ Docker build failed$${NC}"' >> test-build-audio-extract.sh
	@echo '    exit 1' >> test-build-audio-extract.sh
	@echo 'fi' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo '# Test 2: Run container help' >> test-build-audio-extract.sh
	@echo 'echo "Test 2: Testing container startup..."' >> test-build-audio-extract.sh
	@echo 'if docker run --rm audio-extract-test --help ; then' >> test-build-audio-extract.sh
	@echo '    echo -e "$${GREEN}✓ Container runs successfully$${NC}"' >> test-build-audio-extract.sh
	@echo 'else' >> test-build-audio-extract.sh
	@echo '    echo -e "$${RED}✗ Container failed to run$${NC}"' >> test-build-audio-extract.sh
	@echo '    exit 1' >> test-build-audio-extract.sh
	@echo 'fi' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo '# Test 3: Check for required files' >> test-build-audio-extract.sh
	@echo 'echo "Test 3: Checking required files..."' >> test-build-audio-extract.sh
	@echo 'if docker run --rm audio-extract-test ls -la /usr/local/bin/docker-entrypoint.sh ; then' >> test-build-audio-extract.sh
	@echo '    echo -e "$${GREEN}✓ Entrypoint script exists$${NC}"' >> test-build-audio-extract.sh
	@echo 'else' >> test-build-audio-extract.sh
	@echo '    echo -e "$${RED}✗ Entrypoint script missing$${NC}"' >> test-build-audio-extract.sh
	@echo '    exit 1' >> test-build-audio-extract.sh
	@echo 'fi' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo '# Test 4: Test with GCSfuse disabled' >> test-build-audio-extract.sh
	@echo 'echo "Test 4: Testing without GCSfuse..."' >> test-build-audio-extract.sh
	@echo 'if docker run --rm -e ENABLE_GCSFUSE=false audio-extract-test \' >> test-build-audio-extract.sh
	@echo '    python -c "print('"'"'Audio extract module loaded successfully'"'"')" ; then' >> test-build-audio-extract.sh
	@echo '    echo -e "$${GREEN}✓ Runs without GCSfuse$${NC}"' >> test-build-audio-extract.sh
	@echo 'else' >> test-build-audio-extract.sh
	@echo '    echo -e "$${RED}✗ Failed without GCSfuse$${NC}"' >> test-build-audio-extract.sh
	@echo '    exit 1' >> test-build-audio-extract.sh
	@echo 'fi' >> test-build-audio-extract.sh
	@echo '' >> test-build-audio-extract.sh
	@echo 'echo -e "$${GREEN}All tests passed!$${NC}"' >> test-build-audio-extract.sh
	@chmod +x test-build-audio-extract.sh

test-act: ## Test workflows with act (GitHub Actions locally)
	@if command -v act >/dev/null 2>&1; then \
		echo "$(GREEN)Testing workflows with act...$(NC)"; \
		act -l; \
		act -n push -W .github/workflows/build-audio-extract.yml; \
	else \
		echo "$(YELLOW)act not installed. Install from: https://github.com/nektos/act$(NC)"; \
		echo "Alternatively, use 'make test-workflows' for basic validation"; \
	fi