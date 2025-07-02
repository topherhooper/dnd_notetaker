#!/bin/bash
# Quick test script for development config

echo "Audio Extract - Development Test"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "audio_extract_config.yaml.dev" ]; then
    echo "ERROR: Run this from the audio_extract directory"
    exit 1
fi

# Check if credentials exist
CREDS_PATH="/workspaces/dnd_notetaker/.credentials/service_account.json"
if [ ! -f "$CREDS_PATH" ]; then
    echo "ERROR: Service account credentials not found at: $CREDS_PATH"
    echo "Please ensure your credentials file exists at this location"
    exit 1
fi

echo "✓ Found credentials at: $CREDS_PATH"
echo ""

# Test options
echo "Select test option:"
echo "1) Test connection only"
echo "2) Run one check cycle"
echo "3) Start continuous monitoring"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "Testing connection..."
        python -m audio_extract.dev_monitor --config audio_extract_config.yaml.dev --test
        ;;
    2)
        echo "Running one check cycle..."
        python -m audio_extract.dev_monitor --config audio_extract_config.yaml.dev --once
        ;;
    3)
        echo "Starting continuous monitoring (Ctrl+C to stop)..."
        python -m audio_extract.dev_monitor --config audio_extract_config.yaml.dev
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac