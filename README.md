# Meet Notes

Streamlined Google Meet recording processor that automatically generates natural prose-style meeting notes.

## Features

- 📥 **Automatic Download** - Fetches recordings directly from Google Drive
- 🎵 **Audio Extraction** - Optimized audio processing with FFmpeg
- 📝 **AI Transcription** - Accurate transcripts using OpenAI Whisper
- 📖 **Natural Notes** - Flowing prose narrative (no bullets or structure)
- 🌐 **HTML Viewer** - All artifacts in one shareable page
- ⚡ **Smart Processing** - Skips completed expensive operations
- 🐳 **Docker Support** - Zero-setup containerized execution

## Quick Start (Docker - Recommended)
1. **Clone the repository**:
   ```bash
   git clone https://github.com/[username]/dnd_notetaker.git
   cd dnd_notetaker
   ```

2. **One-time setup**:
   ```bash
   make docker-setup
   ```

3. **Configure** (see [Configuration](#configuration) for details):
   - Copy `config.example.json` to `.credentials/config.json` and update values
   - Add your Google service account key to `.credentials/service_account.json`

4. **Run**:
   ```bash
   # Process most recent recording
   make run
   
   # Process specific recording
   make run-file FILE_ID=1a2b3c4d5e6f
   ```

## Prerequisites

### For Docker (Recommended)
- Docker installed on your system
- That's it! Docker handles Python, FFmpeg, and all dependencies

### For Local Development
- Python 3.9+
- FFmpeg (for audio processing)
- Virtual environment (recommended)

#### Install FFmpeg locally:
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows - download from https://ffmpeg.org/download.html
```

## Configuration

### 1. Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Drive API** and **Google Docs API**
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Download the JSON key file
5. Save the key file to `.credentials/service_account.json`
6. Share your Google Drive folder with the service account email

### 2. OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API keys section
4. Create a new API key
5. Add to your config file

## Usage

### Docker Usage (Recommended)

```bash
# Process the most recent Meet recording
make run

# Process a specific recording by file ID
make run-file FILE_ID=1a2b3c4d5e6f

# See all available commands
make help
```

### Local Usage (Development)

```bash
# Setup local environment
make setup
source venv/bin/activate

# Process the most recent Meet recording
python -m dnd_notetaker

# Process a specific recording by file ID
python -m dnd_notetaker 1a2b3c4d5e6f

# Test what would happen without executing (dry-run mode)
python -m dnd_notetaker --dry-run
python -m dnd_notetaker 1a2b3c4d5e6f --dry-run
```

### Dry-Run Mode

The `--dry-run` flag allows you to see what operations would be performed without actually executing them:

```bash
# See what would happen without downloading/processing
python -m dnd_notetaker FILE_ID --dry-run

# Example output:
[DRY RUN] Would download from Google Drive:
  File ID: FILE_ID
  Destination: /path/to/output/meeting.mp4
[DRY RUN] Would extract audio using FFmpeg:
  Input: /path/to/output/meeting.mp4
  Output: /path/to/output/audio.mp3
[DRY RUN] Would transcribe audio using OpenAI Whisper:
  Audio file: /path/to/output/audio.mp3
  Model: gpt-4o-transcribe
  Estimated cost: ~$0.006 per minute
[DRY RUN] Would generate notes using OpenAI GPT:
  Model: o4-mini
  Transcript length: 0 characters
[DRY RUN] Would save artifacts to: /path/to/output/
```

This is useful for:
- Testing configuration changes
- Understanding the processing pipeline
- Debugging without running expensive operations
- Running without credentials for testing

### Output Structure

All outputs are saved to timestamped directories:
```
~/meet_notes_output/
└── 2025_01_19_150230/
    ├── meeting.mp4        # Original recording
    ├── audio.mp3          # Extracted audio
    ├── transcript.txt     # Raw transcription
    ├── notes.txt          # Natural prose notes
    ├── artifacts.json     # Metadata
    └── index.html         # 🌐 View everything here!
```

### Example Notes

The tool generates natural, flowing prose:

> The meeting began with John welcoming everyone and outlining the agenda for the product launch discussion. Sarah immediately raised concerns about the March timeline, particularly emphasizing that the testing phase needed at least two additional weeks to ensure quality. After considerable discussion involving the entire team, they collectively agreed to push the launch to early April. Michael took responsibility for updating the project timeline and committed to communicating the change to all stakeholders by end of week...

## How It Works

1. **Downloads** your Google Meet recording from Drive
2. **Extracts** audio using FFmpeg (optimized for speech)
3. **Transcribes** using OpenAI's Whisper API
4. **Generates** natural prose notes using GPT-4
5. **Creates** an HTML viewer with all artifacts

The tool intelligently skips completed steps if you run it again on the same recording.

## Troubleshooting

### "make run" doesn't work

If you see errors about missing config or service account:

1. **Run the setup helper**:
   ```bash
   ./setup-config.sh
   ```

2. **Check your config**:
   ```bash
   cat .credentials/config.json
   ```
   Make sure:
   - `openai_api_key` is set (starts with `sk-`)
   - `google_service_account` points to your JSON file

3. **Verify service account exists**:
   ```bash
   ls -la .credentials/service_account.json
   ```
   If missing, download from Google Cloud Console

### Other Common Issues

- **FFmpeg not found**: Make sure FFmpeg is installed and in your PATH
- **No recordings found**: Verify your service account has access to the Drive folder
- **API errors**: Check your OpenAI API key has sufficient credits

### Debug Mode

```bash
export LOG_LEVEL=DEBUG
python -m meet_notes
```

## Available Commands

```bash
make help          # Show all available commands
make build         # Build Docker image
make run           # Process most recent recording
make run-file      # Process specific recording
make setup         # Setup local development
make test          # Run test suite
make clean         # Clean build artifacts
```

## Development

### Development Setup

```bash
# Clone repository
git clone https://github.com/[username]/dnd_notetaker.git
cd dnd_notetaker

# Quick setup
make setup
source venv/bin/activate

# Or manually:
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -e .
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=dnd_notetaker
```

### Project Structure

```
dnd_notetaker/
├── Dockerfile                 # Container definition
├── Makefile                   # Simple command interface
├── docker-compose.yml         # Docker Compose config
├── src/dnd_notetaker/
│   ├── meet_notes.py          # Main entry point
│   ├── meet_processor.py      # Pipeline orchestrator
│   ├── audio_extractor.py     # Audio extraction
│   ├── note_generator.py      # GPT-4 notes generation
│   ├── artifacts.py           # Output management
│   └── config.py              # Configuration
└── tests/                     # Test suite
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- OpenAI Whisper for transcription
- GPT-4 for natural language processing
- Google APIs for Drive integration
- FFmpeg for audio processing