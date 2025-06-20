#!/bin/bash

# Configuration setup helper for Meet Notes

set -e

echo "🎬 Meet Notes Configuration Setup"
echo "================================="
echo ""

# Ensure config directory exists
mkdir -p .credentials

# Check if config already exists
if [ -f .credentials/config.json ]; then
    echo "✅ Config file already exists at: .credentials/config.json"
    echo ""
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing configuration."
        exit 0
    fi
fi

# Get OpenAI API key
echo ""
echo "📝 OpenAI API Key Setup"
echo "Get your key from: https://platform.openai.com/api-keys"
read -p "Enter your OpenAI API key (sk-...): " openai_key

# Get service account path
echo ""
echo "📝 Google Service Account Setup"
echo "Default path: .credentials/service_account.json"
read -p "Enter path to service account JSON (or press Enter for default): " service_account
if [ -z "$service_account" ]; then
    service_account=".credentials/service_account.json"
fi

# Expand tilde in path
service_account="${service_account/#\~/$HOME}"

# Check if service account file exists
if [ ! -f "$service_account" ]; then
    echo ""
    echo "⚠️  Warning: Service account file not found at: $service_account"
    echo "Make sure to download it from Google Cloud Console and save it there."
fi

# Create config
cat > .credentials/config.json << EOF
{
  "openai_api_key": "${openai_key}",
  "google_service_account": "${service_account}",
  "output_dir": "./meet_notes_output"
}
EOF

echo ""
echo "✅ Configuration saved to: .credentials/config.json"
echo ""
echo "Next steps:"
echo "1. Download your Google service account key if you haven't already"
echo "2. Save it to: $service_account"
echo "3. Run: make run"
echo ""
echo "For more information, see README.md"