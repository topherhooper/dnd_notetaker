#!/bin/bash
set -e

echo "Testing Docker build locally..."

# Colors for output
GREEN="[0;32m"
RED="[0;31m"
NC="[0m" # No Color

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
# First check what's in the container
echo "Checking container contents..."
docker run --rm --entrypoint /bin/bash audio-extract-test -c "ls -la /usr/local/bin/docker-entrypoint.sh" || true
docker run --rm --entrypoint /bin/bash audio-extract-test -c "ls -la /app/" || true
docker run --rm --entrypoint /bin/bash audio-extract-test -c "ls -la /app/audio_extract/" || true
docker run --rm --entrypoint /bin/bash audio-extract-test -c "echo PYTHONPATH=\$PYTHONPATH" || true
if docker run --rm audio-extract-test --help 2>&1 ; then
    echo -e "${GREEN}✓ Container runs successfully${NC}"
else
    echo -e "${RED}✗ Container failed to run${NC}"
    # Debug: Check Python path
    docker run --rm --entrypoint /bin/bash audio-extract-test -c "cd /app && python -c 'import sys; print(sys.path)'" || true
    exit 1
fi

# Test 3: Check for required files
echo "Test 3: Checking required files..."
if docker run --rm --entrypoint /bin/bash audio-extract-test -c "ls -la /usr/local/bin/docker-entrypoint.sh" ; then
    echo -e "${GREEN}✓ Entrypoint script exists${NC}"
else
    echo -e "${RED}✗ Entrypoint script missing${NC}"
    exit 1
fi

# Test 4: Test with GCSfuse disabled and show help
echo "Test 4: Testing without GCSfuse..."
if docker run --rm -e ENABLE_GCSFUSE=false audio-extract-test --help ; then
    echo -e "${GREEN}✓ Runs without GCSfuse${NC}"
else
    echo -e "${RED}✗ Failed without GCSfuse${NC}"
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
