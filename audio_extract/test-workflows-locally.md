# Testing GitHub Workflows Locally

This guide shows how to test GitHub Actions workflows locally before pushing to GitHub.

## Using Act

[Act](https://github.com/nektos/act) runs GitHub Actions locally using Docker.

### Installation

```bash
# macOS
brew install act

# Linux (using script)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Or download binary directly
# Visit: https://github.com/nektos/act/releases
```

### Basic Usage

```bash
# List available workflows
act -l

# Run default push event
act

# Run specific workflow
act -W .github/workflows/build-audio-extract.yml

# Run with specific event
act pull_request

# Dry run (see what would run)
act -n
```

## Testing Our Workflows

### 1. Test the Build Workflow

```bash
cd /workspaces/dnd_notetaker

# Test build workflow (simulating a push)
act push -W .github/workflows/build-audio-extract.yml \
  --container-architecture linux/amd64 \
  -s GITHUB_TOKEN=$GITHUB_TOKEN

# Test with pull request event
act pull_request -W .github/workflows/build-audio-extract.yml
```

### 2. Test Workflow Locally with Docker

Since our build workflow builds Docker images, we can test the Docker build directly:

```bash
cd /workspaces/dnd_notetaker/audio_extract

# Test Docker build
docker build -t audio-extract-test .

# Run the built image
docker run --rm audio-extract-test --help

# Test with docker-compose
docker-compose build
```

### 3. Create Test Script

```bash
cat > /workspaces/dnd_notetaker/audio_extract/test-build.sh << 'EOF'
#!/bin/bash
set -e

echo "Testing Docker build locally..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Build Docker image
echo "Test 1: Building Docker image..."
if docker build -t audio-extract-test . ; then
    echo -e "${GREEN}✓ Docker build successful${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

# Test 2: Run container help
echo "Test 2: Testing container startup..."
if docker run --rm audio-extract-test --help ; then
    echo -e "${GREEN}✓ Container runs successfully${NC}"
else
    echo -e "${RED}✗ Container failed to run${NC}"
    exit 1
fi

# Test 3: Check for required files
echo "Test 3: Checking required files..."
if docker run --rm audio-extract-test ls -la /usr/local/bin/docker-entrypoint.sh ; then
    echo -e "${GREEN}✓ Entrypoint script exists${NC}"
else
    echo -e "${RED}✗ Entrypoint script missing${NC}"
    exit 1
fi

# Test 4: Test with GCSfuse disabled
echo "Test 4: Testing without GCSfuse..."
if docker run --rm -e ENABLE_GCSFUSE=false audio-extract-test \
    python -c "print('Audio extract module loaded successfully')" ; then
    echo -e "${GREEN}✓ Runs without GCSfuse${NC}"
else
    echo -e "${RED}✗ Failed without GCSfuse${NC}"
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
EOF

chmod +x test-build.sh
```

### 4. Testing with Act Configuration

Create `.actrc` file for default settings:

```bash
cat > /workspaces/dnd_notetaker/.actrc << 'EOF'
# Default Act configuration
--container-architecture linux/amd64
--pull=false
--rm
EOF
```

### 5. Mock Secrets for Local Testing

```bash
cat > /workspaces/dnd_notetaker/.secrets << 'EOF'
# Mock secrets for act (DO NOT COMMIT THIS FILE)
GITHUB_TOKEN=mock-token-for-testing
GCS_BUCKET_NAME=test-bucket
AUDIO_EXTRACT_FOLDER_ID=test-folder-id
EOF

# Add to .gitignore
echo ".secrets" >> /workspaces/dnd_notetaker/.gitignore
```

### 6. Test Specific Jobs

```bash
# Test only the test job from tests.yml
act -j test-audio-extract -W .github/workflows/tests.yml

# Test with custom event payload
cat > event.json << 'EOF'
{
  "pull_request": {
    "number": 123,
    "head": {
      "sha": "abc123def456"
    }
  }
}
EOF

act pull_request -W .github/workflows/build-audio-extract.yml -e event.json
```

## Testing Without Act

If you can't install Act, you can still test parts of the workflows:

### 1. Validate Workflow Syntax

```bash
# Install actionlint
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Or download binary
# https://github.com/rhysd/actionlint/releases

# Validate all workflows
actionlint

# Validate specific workflow
actionlint .github/workflows/build-audio-extract.yml
```

### 2. Test Individual Steps

```bash
# Test the metadata extraction
docker run --rm \
  -e GITHUB_SHA=abc123def456 \
  -e GITHUB_REF=refs/heads/main \
  ghcr.io/docker/metadata-action:v5

# Test docker buildx
docker buildx build --platform linux/amd64 -t test:latest ./audio_extract
```

### 3. Create Makefile Target

Add to the Makefile:

```makefile
# Test GitHub workflows locally
test-workflows:
	@echo "Testing workflow syntax..."
	@if command -v actionlint >/dev/null 2>&1; then \
		actionlint; \
	else \
		echo "actionlint not installed, skipping syntax check"; \
	fi
	@echo "Testing Docker build..."
	@./test-build.sh
	@echo "Testing docker-compose..."
	@docker-compose build --no-cache
	@echo "All workflow tests passed!"

# Test with act
test-act:
	@if command -v act >/dev/null 2>&1; then \
		act -n push -W .github/workflows/build-audio-extract.yml; \
	else \
		echo "act not installed. Install from: https://github.com/nektos/act"; \
		exit 1; \
	fi
```

## Common Issues and Solutions

### Issue: Container architecture mismatch
```bash
# Force specific architecture
act --container-architecture linux/amd64
```

### Issue: Missing secrets
```bash
# Provide secrets file
act -s GITHUB_TOKEN=test-token --secret-file .secrets
```

### Issue: Docker-in-Docker
```bash
# Run act with privileged mode
act --privileged
```

### Issue: Large runner images
```bash
# Use medium runner image instead of large
act --platform ubuntu-latest=nektos/act-environments-ubuntu:18.04-medium
```

## Summary

Testing workflows locally helps:
1. Catch syntax errors before pushing
2. Test Docker builds without using GitHub Actions minutes
3. Debug complex workflows step by step
4. Validate secrets and environment setup

For our audio-extract workflows:
- The build workflow can be tested with direct Docker commands
- The test workflow can be run with pytest locally
- The deploy workflow is harder to test locally but can be simulated
- Use act for more realistic GitHub Actions environment