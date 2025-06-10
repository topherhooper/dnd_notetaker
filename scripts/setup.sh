#!/bin/bash

echo "=== D&D Notetaker Setup Script ==="
echo

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for ffmpeg
echo
echo "Checking for ffmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    echo "✓ ffmpeg is installed"
    ffmpeg -version | head -n1
else
    echo "✗ ffmpeg is not installed"
    echo "Please install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
fi

echo

# Script is now in scripts/ directory, so go to parent
cd "$(dirname "$0")/.."

# Create config template if it doesn't exist
if [ ! -f .credentials/config.json ]; then
    echo "Creating config template..."
    mkdir -p .credentials
    cat > .credentials/config.json << EOF
{
    "email": {
        "email": "your_email@gmail.com",
        "password": "your_password",
        "imap_server": "imap.gmail.com"
    },
    "openai_api_key": "your_openai_api_key"
}
EOF
fi

# Create output directory for processed files
echo "Creating output directory..."
mkdir -p output

# Create .credentials directory
echo "Creating credentials directory..."
mkdir -p .credentials
chmod 700 .credentials

# Create test directory
echo "Creating test directory..."
mkdir -p tests

# Install package in development mode
echo
echo "Installing package in development mode..."
pip install -e .

# Run tests to verify setup
echo
echo "Running tests to verify setup..."
python -m pytest tests/test_utils.py -v --tb=short || echo "Note: Some tests may fail if dependencies are not fully configured."

echo
echo "=== Setup completed! ==="
echo

# Ask if user wants to set up credentials now
echo "Would you like to set up your credentials now? (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo
    python scripts/setup_credentials.py
else
    echo
    echo "You can set up credentials later by running:"
    echo "  python scripts/setup_credentials.py"
fi

echo
echo "Next steps:"
echo "1. Set up credentials (if not done): python scripts/setup_credentials.py"
echo "2. Add Google Service Account credentials to .credentials/service_account.json"
echo "3. Run tests: python -m pytest"
echo "4. Process a session: python -m dnd_notetaker.main process"
echo "   Or use the Makefile: make process"
echo
echo "Note: Virtual environment is now activated. To reactivate later:"
echo "  source venv/bin/activate"