#!/bin/bash

echo "=== D&D Notetaker Demo Setup ==="
echo
echo "This demo shows how the credential setup process works."
echo "Press Ctrl+C at any time to exit."
echo

# Create a demo directory
DEMO_DIR="demo_setup_test"
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

echo "Created demo directory: $DEMO_DIR"
echo

# Run the setup script
echo "Running credential setup..."
echo "(This is just a demo - enter fake credentials)"
echo
python setup_credentials.py

echo
echo "Demo complete! Files created in $DEMO_DIR/.credentials/"
echo

# Show what was created
if [ -d ".credentials" ]; then
    echo "Contents of .credentials directory:"
    ls -la .credentials/
    echo
    
    if [ -f ".credentials/config.json" ]; then
        echo "Config file permissions:"
        ls -l .credentials/config.json
        echo
        echo "Config file contents (passwords hidden):"
        python -c "
import json
with open('.credentials/config.json', 'r') as f:
    config = json.load(f)
    if 'email' in config and 'password' in config['email']:
        config['email']['password'] = '***hidden***'
    if 'openai_api_key' in config:
        config['openai_api_key'] = config['openai_api_key'][:6] + '...' + config['openai_api_key'][-4:]
    print(json.dumps(config, indent=2))
"
    fi
fi

echo
echo "To clean up this demo, run: rm -rf $DEMO_DIR"