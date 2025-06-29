# Audio Extract Module

A standalone audio extraction service that monitors Google Drive for new Meet recordings and automatically extracts audio. Designed with a "fail fast" philosophy - no try/except blocks, all errors bubble up with full stack traces.

## Features

- **Google Drive monitoring** - Continuously monitor Drive folders for new Meet recordings
- **FFmpeg-based extraction** - Reliable audio extraction from video files
- **Processing tracker** - SQLite database tracks all processed files
- **Config-driven behavior** - Dev and prod configs control everything
- **Web dashboard** (dev only) - Real-time monitoring at http://localhost:8080
- **Email notifications** (prod only) - Get notified when processing fails
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
│   └── monitor.py       # Monitoring service
├── cli/                 # CLI tools
│   ├── __init__.py
│   └── monitor.py       # Drive monitoring CLI
├── config.py            # Configuration management
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

The audio_extract module is designed to be isolated from the main project. Set it up in its own virtual environment:

```bash
# Navigate to the audio_extract directory
cd audio_extract/

# Create a dedicated virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install the module in development mode
pip install -e .

# For development with testing tools:
pip install -e ".[dev]"
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

### Run All Tests

```bash
# Run the complete test suite
python run_all_tests.py
```

### Individual Test Suites

```bash
# Unit tests (51 tests)
python run_tests.py

# CLI tools functionality
python test_cli_tools.py

# Dashboard server tests
python test_dashboard.py

# Full integration test
python test_full_integration.py
```

### Using pytest directly

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_extractor.py -v

# Run with coverage
pytest tests/ --cov=audio_extract --cov-report=html
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

## Config-Driven Behavior

| Setting | Dev | Prod |
|---------|-----|------|
| Run mode | Foreground (see output) | Background daemon |
| Web dashboard | Yes (auto-opens) | No |
| Check interval | 60 seconds | 5 minutes |
| On error | **EXIT with full trace** | Email & continue |
| Log level | DEBUG | INFO |
| Keep videos | Yes | No (delete after) |

## How It Works

1. **Monitors** your Google Drive folder for new Meet recordings
2. **Downloads** new video files to a temp directory
3. **Extracts** audio using FFmpeg
4. **Tracks** processed files in SQLite database (won't reprocess)
5. **Notifies** on failure (email in prod, console in dev)

## Error Philosophy

This module uses a **"fail fast"** approach:
- **No try/except blocks** - errors bubble up immediately
- **Full stack traces** - see exactly what went wrong
- **Dev mode exits on error** - fix issues immediately
- **Prod mode emails on error** - but keeps running via process manager

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

For production, use a process manager to handle restarts:

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
