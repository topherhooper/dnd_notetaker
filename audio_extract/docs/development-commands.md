# Development Commands

This document provides a quick reference for common development commands using the Makefile.

## Running the Monitor

### Basic Development Mode
```bash
make run
```
- Starts the monitor in development mode
- Health check endpoint is disabled for simpler operation
- Monitors continuously until stopped with Ctrl+C

### Single Check Cycle
```bash
make run-once
```
- Runs one check cycle and exits
- Useful for testing or cron jobs
- Health check endpoint is disabled

### With Health Check Endpoint
```bash
make run-with-health
```
- Starts monitor with health check endpoint on port 8081
- Access health status at http://localhost:8081/health
- Includes readiness and liveness probes

## Testing

### Run All Tests
```bash
make test
```
Runs the complete test suite (98 tests)

### Run Specific Test Categories
```bash
make test-cli        # Test CLI commands
make test-unit       # Unit tests only
make test-integration # Integration tests
make test-storage    # Storage module tests
```

### Test Coverage
```bash
make coverage
```
Generates HTML coverage report in `htmlcov/`

## Common Issues and Solutions

### Flask Module Not Found
If you see `ModuleNotFoundError: No module named 'flask'`:
```bash
make install         # Install all dependencies
# or
pip install flask    # Install Flask specifically
```

### Connection Testing
Before running the monitor, test your Google Drive connection:
```bash
make test-connection
```

### Dashboard Only
To run just the web dashboard without monitoring:
```bash
make dashboard
```

## Development Workflow

1. **Test Connection**: `make test-connection`
2. **Run Once**: `make run-once` (verify it finds files)
3. **Run Continuously**: `make run` (for development)
4. **Run Tests**: `make test` (before committing)

## Configuration

The monitor uses `audio_extract_config.dev.yaml` by default. Key settings:
- Google Drive folder ID
- Output directory
- Check interval
- Storage configuration

See `audio_extract_config.dev.yaml` for all options.