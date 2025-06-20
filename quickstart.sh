#!/bin/bash

# Quick start script for Meet Notes

set -e

echo "🎬 Meet Notes Quick Start"
echo "========================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Run docker setup
echo "📁 Setting up directories..."
make docker-setup

# Copy example config if not exists
if [ ! -f ~/.meet_notes/config.json ]; then
    echo ""
    echo "📝 Creating config file..."
    cp config.example.json ~/.meet_notes/config.json
    echo "✅ Config template created at: ~/.meet_notes/config.json"
    echo ""
    echo "⚠️  Please edit ~/.meet_notes/config.json and add:"
    echo "   1. Your OpenAI API key"
    echo "   2. Path to your Google service account JSON file"
    echo ""
    echo "Need help? See the Configuration section in README.md"
else
    echo "✅ Config file already exists"
fi

echo ""
echo "🔨 Building Docker image..."
make build

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit ~/.meet_notes/config.json with your API keys"
echo "2. Add your Google service account key"
echo "3. Run: make run"
echo ""
echo "For more information, see README.md"