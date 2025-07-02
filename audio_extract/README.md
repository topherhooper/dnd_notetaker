# Audio Extract Module

A standalone audio extraction service that monitors Google Drive for new Meet recordings and automatically extracts audio. Designed with a "fail fast" philosophy - no try/except blocks, all errors bubble up with full stack traces.

## Features

- **Google Drive monitoring** - Continuously monitor Drive folders for new Meet recordings
- **FFmpeg-based extraction** - Reliable audio extraction from video files
- **Processing tracker** - SQLite database tracks all processed files
- **Storage abstraction** - Support for local and Google Cloud Storage
- **Config-driven behavior** - Dev and prod configs control everything
- **Web dashboard** (dev only) - Real-time monitoring at http://localhost:8080
- **Health check endpoints** - Production-ready monitoring at /health, /ready, /live
- **Docker support** - Easy deployment with Docker and docker-compose
- **No error hiding** - All errors propagate with full stack traces for debugging

## Project Structure

```
audio_extract/
├── __init__.py          # Module exports
├── extractor.py         # Core audio extraction
├── chunker.py           # Audio file chunking
├── tracker.py           # Processing history tracking
├── utils.py             # Utility functions
├── exceptions.py        # Custom exceptions
├── dev_extract.py       # CLI for extraction
├── dev_status.py        # CLI for status checking
├── dev_server.py        # Web dashboard server
├── dashboard/           # Web dashboard files
│   ├── index.html
│   ├── server.py
│   └── static/
│       ├── style.css
│       └── app.js
├── tests/               # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_chunker.py
│   ├── test_exceptions.py
│   ├── test_extractor.py
│   ├── test_tracker.py
│   └── test_utils.py
├── drive/               # Google Drive integration
│   ├── __init__.py
│   ├── auth.py          # Authentication helpers
│   ├── client.py        # Drive API client
│   ├── monitor.py       # Monitoring service
│   └── storage_monitor.py  # Storage-aware monitor
├── storage/             # Storage abstraction
│   ├── __init__.py
│   ├── base.py          # Abstract storage interface
│   ├── factory.py       # Storage factory
│   ├── local_storage.py # Local filesystem storage
│   ├── gcs_storage.py   # Google Cloud Storage
│   └── db_migrations.py # Database schema updates
├── cli/                 # CLI tools
│   ├── __init__.py
│   └── monitor.py       # Drive monitoring CLI
├── config.py            # Configuration management
├── health.py            # Health check endpoints
├── Dockerfile           # Docker container definition
├── docker-compose.yml   # Development Docker setup
├── docker-compose.prod.yml  # Production Docker setup
├── nginx.conf           # Nginx reverse proxy config
├── run_tests.py         # Test runner
├── run_all_tests.py     # Comprehensive test suite
├── test_cli_tools.py    # CLI functionality tests
├── test_dashboard.py    # Dashboard tests
├── test_full_integration.py  # Integration tests
├── test_drive_integration.py  # Drive integration tests
├── setup.py            # Package configuration
├── requirements.txt    # Dependencies
├── pytest.ini          # Pytest configuration
├── MANIFEST.in         # Package manifest
├── README.md          # This file
├── LICENSE            # MIT License
└── .gitignore         # Git ignore rules
```

## Quick Start with Make

A comprehensive Makefile is provided for easy development. All Python commands automatically use a virtual environment:

```bash
# Show all available commands
make help

# Complete development setup (creates venv automatically)
make setup-dev

# Run tests (uses venv/bin/python)
make test

# Start monitoring (uses venv/bin/python)
make run

# Build and run with Docker
make docker-run
```

The virtual environment is created automatically at `./venv/` when you run any Python-based command. No need to activate it manually - the Makefile handles it for you.

## Installation

### Prerequisites

1. **FFmpeg** - Required for audio extraction:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

2. **Google Drive API** (optional) - For Drive monitoring:
- Create a service account in Google Cloud Console
- Enable Google Drive API
- Download service account credentials JSON

### Setup as Standalone Module

The audio_extract module is designed to be isolated from the main project. The Makefile automatically manages the virtual environment:

```bash
# Navigate to the audio_extract directory
cd audio_extract/

# Run setup (creates venv and installs dependencies)
make setup-dev

# The virtual environment is used automatically by all make commands
# If you need to activate it manually:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Or just use make commands which handle the venv automatically:
make install       # Installs all dependencies
make install-dev   # Installs dev dependencies too
```

### Install from Package

```bash
# Install the module and its CLI tools
pip install -e /path/to/audio_extract/

# This installs three command-line tools:
# - audio-extract: Extract audio from videos
# - audio-status: Check processing status
# - audio-dashboard: Run the web dashboard
```

Note: The audio_extract module requires Google Drive API dependencies for monitoring functionality. See requirements.txt for the full list.

## Quick Start

### Extract Audio from Video

```python
from audio_extract import AudioExtractor

extractor = AudioExtractor()
extractor.extract('input_video.mp4', 'output_audio.mp3')
```

### Track Processing

```python
from audio_extract import ProcessingTracker

tracker = ProcessingTracker('processed_videos.db')

# Check if already processed
if not tracker.is_processed('video.mp4'):
    # Extract audio...
    tracker.mark_processed('video.mp4', status='completed')
```

### Split Large Audio Files

```python
from audio_extract import AudioChunker

chunker = AudioChunker(max_size_mb=24)
chunks = chunker.split('large_audio.mp3', 'output_dir/')
```

## Development Tools

### Command Line Interface

After installation, use the provided CLI tools:

```bash
# After installation with pip install -e .
# Note: Console scripts require proper package structure
# For now, use the Python module approach below
```

Run as Python modules from the parent directory:

```bash
# Extract audio with tracking
python -m audio_extract.dev_extract --video input.mp4 --output ./output

# Check processing status
python -m audio_extract.dev_status --recent 7

# Run web dashboard
python -m audio_extract.dev_server --port 8080
```

### Web Dashboard

Start the dashboard server:

```bash
python -m audio_extract.dev_server
```

Then open `http://localhost:8080` in your browser to see:

- Processing statistics
- Recent and failed jobs
- Quick actions for reprocessing

## Storage Options

The module supports multiple storage backends for extracted audio files:

### 1. Local Storage (Default)

```yaml
storage:
  type: local
  local:
    path: ./output  # Where to save audio files
```

### 2. Google Cloud Storage (GCS)

```yaml
storage:
  type: gcs
  gcs:
    bucket_name: my-audio-extracts
    credentials_path: /path/to/gcs-service-account.json
    public_access: false  # Use signed URLs
    url_expiration_hours: 24
```

### 3. GCS via gcsfuse (Recommended for Development)

Mount your GCS bucket as a local filesystem:

```bash
# Install gcsfuse
sudo apt-get install gcsfuse  # Ubuntu/Debian
brew install --cask macfuse && brew install gcsfuse  # macOS

# Mount bucket
gcsfuse --implicit-dirs my-bucket ~/audio-mount

# Configure as local storage
storage:
  type: local
  local:
    path: ~/audio-mount/audio
```

Benefits:
- No code changes between dev/prod
- Files appear in GCS instantly
- Simple file browsing
- Cost effective (no API calls)

## Health Monitoring

The service provides health check endpoints for production monitoring:

- `/health` - Overall health status
- `/ready` - Readiness check
- `/live` - Liveness check

Access at `http://localhost:8081/health` (configurable with `--health-port`)

## Docker Deployment

### Development

```bash
# Build and run with docker-compose
docker-compose up --build

# Or run with custom config
docker-compose run audio-extract --config /app/configs/custom.yaml
```

### Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Check health
curl http://localhost/health
```

The production setup includes:
- Nginx reverse proxy
- Health check endpoints
- Resource limits
- Log rotation
- Automatic restarts

## API Reference

### AudioExtractor

```python
AudioExtractor(config=None, bitrate='128k', sample_rate=44100, channels=1)
```

- `extract(video_path, output_path, progress_callback=None)` - Extract audio from video
- `get_video_info(video_path)` - Get video duration and metadata

### ProcessingTracker

```python
ProcessingTracker(db_path)
```

- `mark_processed(file_path, status, metadata=None)` - Mark video as processed
- `is_processed(file_path)` - Check if video was processed
- `get_metadata(file_path)` - Get processing metadata
- `get_recent_processed(days=7)` - Get recently processed videos
- `get_failed_videos()` - Get all failed processing attempts
- `get_statistics()` - Get processing statistics

### AudioChunker

```python
AudioChunker(max_size_mb=24, chunk_duration_minutes=15)
```

- `split(audio_path, output_dir, progress_callback=None)` - Split audio into chunks
- `cleanup()` - Clean up temporary files

## Testing

The module includes a comprehensive test suite with unit tests, integration tests, and functional tests.

### Using Make Commands (Recommended)

```bash
# Run all tests (uses venv automatically)
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run with coverage report
make coverage
```

### Manual Test Running

If you prefer to run tests manually:

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_extractor.py -v

# Run with coverage
python -m pytest tests/ --cov=audio_extract --cov-report=html
```

### Test Coverage

The test suite includes:
- **Unit tests**: All core modules (extractor, chunker, tracker, utils, exceptions)
- **Integration tests**: End-to-end workflow with real FFmpeg operations
- **CLI tests**: Command-line interface functionality
- **Dashboard tests**: Web server and API endpoints
- **Error handling**: Edge cases and failure scenarios

## Error Handling

The module provides specific exceptions:

- `AudioExtractionError` - Base exception for all errors
- `FFmpegNotFoundError` - FFmpeg is not installed
- `InvalidAudioFileError` - Audio file is invalid or inaccessible
- `ChunkingError` - Error during audio splitting
- `TrackingError` - Database operation failed

## Quick Start

### 1. Prerequisites

- **FFmpeg** installed (`apt install ffmpeg` or `brew install ffmpeg`)
- **Google Service Account** with access to your Drive folder
- **Python 3.8+**

### 2. Install Dependencies

```bash
cd /workspaces/dnd_notetaker/audio_extract

# Using make (recommended - handles venv automatically):
make install

# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Two config files are provided:
- `audio_extract_config.dev.yaml` - Development (dashboard, verbose logging, fail on error)
- `audio_extract_config.prod.yaml` - Production (daemon mode, email alerts, keep running)

Update the dev config with your folder ID:
```yaml
google_drive:
  recordings_folder_id: "YOUR_FOLDER_ID_HERE"  # From Drive URL
  service_account_file: /path/to/credentials.json
```

### 4. Test Connection

```bash
python -m audio_extract.dev_monitor --config audio_extract_config.dev.yaml --test
```

### 5. Run

**Development Mode:**
```bash
# Runs in foreground, opens dashboard, exits on any error
python -m audio_extract.dev_monitor --config audio_extract_config.dev.yaml
```

**Production Mode:**
```bash
# Runs as daemon, emails on failure, keeps running
python -m audio_extract.dev_monitor --config audio_extract_config.prod.yaml
```

## How It Works

1. **Monitors** your Google Drive folder for new Meet recordings
2. **Downloads** new video files to a temp directory
3. **Extracts** audio using FFmpeg
4. **Tracks** processed files in SQLite database (won't reprocess)
5. **Notifies** on failure (email in prod, console in dev)

## Error Philosophy

This module uses a **"fail fast"** approach:
- **No try/except blocks** - errors bubble up immediately with full stack traces
- **Full visibility** - see exactly what went wrong and where
- **Dev mode exits on error** - fix issues immediately
- **Prod mode emails on error** - but keeps running via process manager

**Why no try/except?**
- Makes debugging MUCH easier during development
- Real errors are visible immediately, not hidden
- Production resilience comes from process managers (systemd, supervisor)
- Exceptions are for truly exceptional cases only

**When try/except is OK:**
- Checking for optional dependencies (e.g., `import google.cloud.storage`)
- External API calls that might legitimately fail
- Resource cleanup that must happen even on error
- Top-level error reporting (but still re-raise)

## Common Commands

```bash
# Test connection only
python -m audio_extract.dev_monitor --config CONFIG_FILE --test

# Run one check cycle
python -m audio_extract.dev_monitor --config CONFIG_FILE --once

# Start monitoring
python -m audio_extract.dev_monitor --config CONFIG_FILE

# Override config settings
python -m audio_extract.dev_monitor --config CONFIG_FILE --folder-id OTHER_FOLDER --interval 30
```

## Production Deployment

### Using Docker (Recommended)

1. Build the image:
```bash
docker build -t audio-extract .
```

2. Run with docker-compose:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. Check logs:
```bash
docker-compose logs -f audio-extract
```

### Using systemd

For production without Docker, use a process manager to handle restarts:

**systemd example:**
```ini
[Unit]
Description=Audio Extract Monitor
After=network.target

[Service]
Type=simple
User=audioextract
WorkingDirectory=/opt/audio_extract
Environment="GOOGLE_APPLICATION_CREDENTIALS=/etc/audio-extract/credentials.json"
ExecStart=/usr/bin/python3 -m audio_extract.dev_monitor --config /etc/audio-extract/config.prod.yaml
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

**"No Google credentials found"**
- Check service account file path in config
- Ensure file exists and is readable
- Try setting GOOGLE_APPLICATION_CREDENTIALS env var

**"FFmpeg not found"**
- Install FFmpeg: `apt install ffmpeg` or `brew install ffmpeg`
- Check PATH includes FFmpeg location

**Dashboard won't open**
- Only available in dev mode
- Check port 8080 is not in use
- Try accessing http://localhost:8080 directly

**Not finding new recordings**
- Verify folder ID is correct (from Drive URL)
- Check service account has access to folder
- Look for recordings with "meet", "recording", or "video" in name

## Quick Make Commands Reference

```bash
# Essential Commands
make help          # Show all available commands
make setup-dev     # One-time development setup
make test          # Run all tests
make run           # Start monitoring (dev mode)
make clean         # Clean temporary files

# Testing
make test-unit     # Unit tests only
make coverage      # Tests with coverage report
make test-connection # Test Drive connection

# Docker
make docker-build  # Build image
make docker-run    # Run in Docker
make docker-logs   # View logs

# Development
make dashboard     # Run dashboard only
make run-once      # Single check cycle
make lint          # Check code quality
make format        # Auto-format code
```
