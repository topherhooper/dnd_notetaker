# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

The D&D Notetaker project follows a standard Python package structure:

```
dnd_notetaker/
├── src/dnd_notetaker/      # Main package source code
│   ├── __init__.py         # Package initialization
│   ├── main.py             # Main entry point and CLI
│   ├── audio_processor.py  # Audio extraction from video
│   ├── transcriber.py      # OpenAI Whisper transcription
│   ├── transcript_processor.py  # GPT-4 text processing
│   ├── docs_uploader.py    # Google Docs upload
│   ├── drive_handler.py    # Google Drive download
│   ├── auth_service_account.py  # Google authentication
│   └── utils.py            # Shared utilities
├── scripts/                # Utility scripts
│   ├── setup.sh           # Setup script
│   ├── cleanup.sh         # Cleanup script
│   ├── setup_credentials.py  # Interactive credential setup
│   └── simple_download_test.py  # Download testing
├── tests/                  # Test suite
├── Makefile               # Build automation
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
└── .credentials/          # API credentials (gitignored)
```

## Commands

### Using Make (Recommended)

```bash
# Complete setup
make setup

# Run the full pipeline
make process
make interactive  # Interactive mode - select from list
make process-name NAME="DnD Thursday Session"
make process-id ID="your-file-id-here"
make process-dir DIR=/path/to/existing/dir

# Individual components
make download
make extract-audio VIDEO=video.mp4
make transcribe AUDIO=audio.mp3
make process-notes TRANSCRIPT=transcript.txt
make upload-docs NOTES=notes.txt TITLE="Session Title"

# Development
make test
make test-coverage
make format
make lint
make clean

# Utilities
make list-sessions
make clean-sessions
make setup-creds
```

### Direct Python Commands

```bash
# Full pipeline
python -m dnd_notetaker.main process
python -m dnd_notetaker.main interactive  # Interactive mode
python -m dnd_notetaker.main process -o custom_directory
python -m dnd_notetaker.main process --keep-temp
python -m dnd_notetaker.main process --name "DnD Thursday Session"
python -m dnd_notetaker.main process --id "your-file-id-here"

# Utility commands
python -m dnd_notetaker.main list     # List temporary directories
python -m dnd_notetaker.main clean    # Clean up old temp files
python -m dnd_notetaker.main clean --age 48  # Clean files older than 48 hours

# Individual components (for testing/debugging)
python -m dnd_notetaker.drive_handler -o output/session_dir
python -m dnd_notetaker.audio_processor -i "video.mp4" -o output/session_dir
python -m dnd_notetaker.transcriber -i audio.mp3 -o output/session_dir
python -m dnd_notetaker.transcript_processor -i transcript.txt -o output/session_dir
python -m dnd_notetaker.docs_uploader -i notes.txt -t "Session Title"
```

## High-Level Architecture

This is a pipeline-based D&D session recording processor:

1. **Drive Download** (`drive_handler.py`) → Downloads recordings directly from Google Drive
2. **Audio Extraction** (`audio_processor.py`) → Extracts and chunks audio from video files
3. **Transcription** (`transcriber.py`) → Converts audio to text using OpenAI Whisper
4. **Processing** (`transcript_processor.py`) → Structures transcript into narrative notes using GPT-4
5. **Upload** (`docs_uploader.py`) → Creates Google Docs with processed notes
   - Documents are automatically shared publicly with anyone who has the link (read-only access)
   - This can be disabled with the `--no-public-share` flag when using the uploader directly

Key architectural principles:
- Each component can run independently for testing/debugging
- Comprehensive error handling and logging throughout
- All processing happens directly in the output directory (no system temp files)
- Automatic directory organization based on session metadata
- Smart checkpointing system that skips completed steps:
  - Skips entire session if already processed
  - Skips audio extraction if `session_audio.mp3` exists
  - Skips transcript generation if `full_transcript_*.txt` exists
  - Always runs processing and upload steps for flexibility
- All sensitive data in `.credentials/` directory
- Generated Google Docs are publicly accessible by default for easy sharing

## Configuration Requirements

### API Credentials

The application requires credentials stored in `.credentials/`:
- `config.json` - OpenAI API key and optional Drive folder ID
- `service_account.json` - Google Service Account credentials

### Required APIs

- Google Drive API (for downloading recordings)
- Google Docs API (for uploading notes)
- OpenAI API (for transcription and text processing)

### System Dependencies

- Python 3.9+
- FFmpeg (for audio/video processing)

## Authentication

The application exclusively uses Google Service Account authentication (no OAuth/interactive login required):

1. Create a service account in Google Cloud Console
2. Enable Drive and Docs APIs
3. Download the service account JSON key
4. Save as `.credentials/service_account.json`
5. Ensure the service account has the following permissions:
   - `drive.readonly` - Read access to Drive files
   - `drive.file` - Manage files created by the app (required for sharing)
   - `documents` - Create and edit Google Docs

Service accounts work without interactive login, making them ideal for automation.

**Note**: After changing authentication scopes, the service account will automatically use the new permissions on next run.

## Development Guidelines

### Testing

- Run tests with `make test` or `python -m pytest`
- Tests use mocking to avoid API calls
- Each component has its own test file
- Use `make test-coverage` for coverage reports

### Code Style

- Use `make format` to format code with black and isort
- Use `make lint` for pylint checks
- Follow PEP 8 guidelines
- Add type hints where beneficial

### Adding Features

1. Create feature branch from main
2. Add tests for new functionality
3. Update documentation if needed
4. Run full test suite
5. Format code before committing

## Common Tasks

### Processing a New Session

```bash
# Quick process with defaults
make process

# Process existing directory (useful for re-running)
make process-dir DIR=output/dnd_sessions_2025_01_10
```

### Debugging Issues

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
make process

# Keep temporary files for inspection
python -m dnd_notetaker.main process --keep-temp

# Test individual components
make download  # Test email download only
make extract-audio VIDEO=test.mp4  # Test audio extraction
```

### Managing Output

```bash
# List all temporary directories
make list-sessions

# Clean old temporary files
make clean-sessions

# Clean all build artifacts
make clean-all
```

## Known Issues & Solutions

### Audio File Size Limits
- Whisper API has 25MB limit
- AudioProcessor automatically chunks large files
- Chunks are transcribed separately and merged

### Google Drive Access
- Service account must have access to the Drive folder
- Share the folder with the service account email
- Folder ID can be configured in config.json

### Processing Interruptions
- The processor checks for existing files
- Re-running skips completed steps
- Use `--dir` flag to resume processing

### Memory Usage
- Large video files are processed in chunks
- Temporary files are cleaned automatically
- Use `--keep-temp` only for debugging