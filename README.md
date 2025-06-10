# D&D Notetaker

Automated D&D session recording processor that transforms Google Meet recordings into structured narrative session notes.

## Features

- **Automated Download**: Downloads session recordings from Gmail/Google Drive
- **Smart Organization**: Automatically creates organized session directories
- **Audio Processing**: Extracts and optimizes audio from video recordings
- **AI Transcription**: Generates accurate transcripts using OpenAI's Whisper API
- **Intelligent Processing**: Transforms raw transcripts into structured narrative notes:
  - Identifies and labels speakers (DM, players, characters)
  - Separates out-of-character discussions
  - Marks important game mechanics moments
  - Highlights memorable quotes and key events
  - Identifies session recap sections
- **Improved Transcript Processing** (v2):
  - Smart chunking for large transcripts
  - Language detection and filtering
  - Cost-effective two-stage processing
  - Better speaker identification
- **Google Docs Integration**: Automatically uploads notes to Google Docs
- **Comprehensive Logging**: Detailed progress tracking and error reporting

## Quick Start

### Using Make (Recommended)

```bash
# Complete setup (virtual environment, dependencies, system checks)
make setup

# Process a session recording
make process

# Process with custom email subject filter
make process-subject SUBJECT="DnD Thursday Session"

# Run tests
make test

# See all available commands
make help
```

### Manual Setup

```bash
# Clone repository
git clone [repository-url]
cd dnd_notetaker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install package in development mode
pip install -e .

# Set up credentials
python scripts/setup_credentials.py
```

## Project Structure

```
dnd_notetaker/
├── src/dnd_notetaker/      # Main package
│   ├── main.py             # Main entry point
│   ├── audio_processor.py  # Audio extraction
│   ├── transcriber.py      # Whisper transcription
│   ├── transcript_processor.py  # GPT-4 processing
│   ├── docs_uploader.py    # Google Docs upload
│   ├── email_handler.py    # Email/Drive download
│   └── utils.py            # Shared utilities
├── scripts/                # Utility scripts
│   ├── setup.sh           # Setup script
│   ├── setup_credentials.py  # Credential setup
├── tests/                  # Test suite
├── Makefile               # Build automation
└── requirements.txt       # Dependencies
```

## Configuration

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### 2. Set Up API Credentials

The application requires:
- Google Service Account with Drive and Docs API access
- OpenAI API key for transcription and processing

Run the credential setup:
```bash
make setup-creds
# Or manually:
python scripts/setup_credentials.py
```

This creates `.credentials/config.json` with your API keys.

### 3. Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API and Google Docs API
4. Create a Service Account with appropriate permissions
5. Download the JSON key file
6. Save as `.credentials/service_account.json`

## Usage

### Full Pipeline

Process a recording from email to Google Docs:
```bash
# Using Make
make process

# Using Python module
python -m dnd_notetaker.main process

# With custom output directory
python -m dnd_notetaker.main process -o custom_directory

# Filter by email subject
python -m dnd_notetaker.main process --subject "DnD Thursday Session"

# Keep temporary files for debugging
python -m dnd_notetaker.main process --keep-temp
```

### Individual Components

Run specific parts of the pipeline:
```bash
# Download recording only
make download

# Extract audio from video
make extract-audio VIDEO=path/to/video.mp4

# Generate transcript
make transcribe AUDIO=path/to/audio.mp3

# Process transcript into notes
make process-notes TRANSCRIPT=path/to/transcript.txt

# Upload to Google Docs
make upload-docs NOTES=path/to/notes.txt TITLE="Session Title"
```

### Utility Commands

```bash
# List temporary directories
make list-sessions

# Clean up old temporary files
make clean-sessions

# Run tests with coverage
make test-coverage

# Format code
make format

# Run linting
make lint
```


## Directory Organization

The processor automatically creates organized directories based on recording filenames:

**Input**: `"DnD - 2025-01-10 18-41 CST - Recording.mp4"`

**Creates**:
```
output/
└── dnd_sessions_2025_01_10/
    ├── DnD - 2025-01-10 18-41 CST - Recording.mp4
    ├── session_audio.mp3
    ├── full_transcript_*.txt
    ├── processed_notes_*.txt
    └── summary_*.json
```

## Smart Checkpointing

The processor includes intelligent checkpointing to avoid redundant work:

1. **Session Already Processed**: If at least 2 key output files exist, the entire session is skipped
2. **Audio Extraction**: Skipped if `session_audio.mp3` already exists
3. **Transcript Generation**: Skipped if `full_transcript_*.txt` already exists (uses most recent)
4. **Resumable Processing**: You can re-run the processor on partial sessions to complete remaining steps

This is especially useful for:
- Recovering from interruptions
- Re-processing with different settings
- Debugging specific pipeline stages

## Development

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific test file
python -m pytest tests/test_audio_processor.py -v
```

### Code Quality

```bash
# Format code with black and isort
make format

# Run linting
make lint

# Clean temporary files
make clean

# Clean everything (including venv)
make clean-all
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Format code (`make format`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg for your system (see Configuration)
2. **API rate limits**: The processor includes automatic retries and chunking
3. **Large files**: Audio is automatically chunked for Whisper API limits
4. **Authentication errors**: Ensure service account has proper permissions

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python -m dnd_notetaker.main process
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI Whisper for transcription
- GPT-4 for intelligent text processing
- Google APIs for Drive and Docs integration
- MoviePy for video processing