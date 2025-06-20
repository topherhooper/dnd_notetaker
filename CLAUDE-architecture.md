# CLAUDE-architecture.md

This file documents the architecture of the D&D Notetaker project. Claude Code is responsible for maintaining this file as the codebase evolves.

## Architecture Overview

The D&D Notetaker provides two interfaces:

1. **Legacy Interface** - Complex multi-mode CLI with various options
2. **Simplified Interface** (NEW) - Streamlined single-purpose tool for Google Meet recordings

### Simplified Architecture (Recommended)

The new simplified interface follows a **pipeline architecture** pattern:

```
Google Drive → Audio Extraction → Transcription → Note Generation → Shareable Artifacts
```

### Legacy Architecture

The original interface supports multiple entry points and complex configurations:

```
Google Drive → Download → Audio Extraction → Transcription → Text Processing → Google Docs
```

## Simplified Interface Classes (NEW)

### 1. MeetProcessor (`meet_processor.py`)
**Purpose**: Main orchestrator for the simplified pipeline

**Key Methods**:
- `process()`: Process a Google Meet recording (with optional file ID)
- `_download_video()`: Download from Drive
- Uses simple checkpointing (file existence checks)

**Dependencies**: All simplified components

### 2. Config (`config.py`)
**Purpose**: Simple configuration management

**Key Features**:
- Auto-creates `.credentials/config.json`
- Manages OpenAI API key, service account path, output directory
- No complex environment variable handling

### 3. AudioExtractor (`audio_extractor.py`)
**Purpose**: Simple audio extraction from video

**Key Methods**:
- `extract()`: Single method to extract audio using FFmpeg
- Optimized for smaller files (mono, 128k bitrate)

**Dependencies**: FFmpeg

### 4. NoteGenerator (`note_generator.py`)
**Purpose**: Generate natural prose-style meeting notes

**Key Methods**:
- `generate()`: Create prose narrative from transcript
- `_split_transcript()`: Handle long transcripts
- `_combine_summaries()`: Merge chunk summaries

**External APIs**: OpenAI GPT-4

### 5. Artifacts (`artifacts.py`)
**Purpose**: Manage and share all meeting artifacts

**Key Methods**:
- `create_share_bundle()`: Generate shareable HTML viewer
- `_create_html_viewer()`: Create interactive web page
- Future: Cloud upload capability

### 6. SimplifiedDriveHandler (`simplified_drive_handler.py`)
**Purpose**: Streamlined Google Drive operations

**Key Methods**:
- `download_file()`: Download by file ID
- `download_most_recent()`: Get latest Meet recording

**External APIs**: Google Drive API

## Legacy Classes (Original Implementation)

### 1. MeetingProcessor (`main.py`)
**Purpose**: Main orchestrator that manages the entire pipeline

**Key Methods**:
- `process()`: Full pipeline execution
- `interactive()`: Interactive session selection
- `list_sessions()`: Display temporary directories
- `clean_sessions()`: Remove old temporary files

**Dependencies**: All other components

### 2. DriveHandler (`drive_handler.py`)
**Purpose**: Downloads video files from Google Drive

**Key Methods**:
- `download_file()`: Download a single file by ID
- `get_shared_items()`: List available files
- `_parse_drive_url()`: Extract file ID from URL

**External APIs**: Google Drive API

### 3. AudioProcessor (`audio_processor.py`)
**Purpose**: Extracts and chunks audio from video files

**Key Methods**:
- `extract_audio()`: Convert video to audio
- `chunk_audio()`: Split large files for API limits
- `get_audio_duration()`: Calculate file duration

**Dependencies**: FFmpeg

### 4. Transcriber (`transcriber.py`)
**Purpose**: Converts audio to text using OpenAI Whisper

**Key Methods**:
- `transcribe_audio()`: Process single audio file
- `transcribe_chunked_audio()`: Handle multiple chunks
- `merge_transcripts()`: Combine chunk transcripts

**External APIs**: OpenAI Whisper API

### 5. TranscriptProcessor (`transcript_processor.py`)
**Purpose**: Structures raw transcript into narrative notes

**Key Methods**:
- `process_transcript()`: Two-stage GPT processing
- `_clean_with_gpt35()`: Initial cleanup
- `_structure_with_gpt4()`: Final structuring

**External APIs**: OpenAI GPT-3.5 and GPT-4

### 6. DocsUploader (`docs_uploader.py`)
**Purpose**: Creates and shares Google Docs

**Key Methods**:
- `upload_notes()`: Create document
- `_share_document()`: Configure sharing permissions

**External APIs**: Google Docs API

### 7. GoogleAuthenticator (`auth_service_account.py`)
**Purpose**: Manages Google service account authentication

**Key Methods**:
- `load_service_account_credentials()`: Load auth file
- `get_drive_service()`: Create Drive client
- `get_docs_service()`: Create Docs client

**Configuration**: `.credentials/service_account.json`

### 8. Utils (`utils.py`)
**Purpose**: Shared utilities and helpers

**Key Functions**:
- `setup_logging()`: Configure application logging
- `load_config()`: Load configuration file
- `get_timestamp()`: Generate timestamps
- `clean_filename()`: Sanitize file names

## Simplified Interface Usage (NEW)

### Entry Point
```bash
# Process most recent recording
python -m meet_notes

# Process specific recording
python -m meet_notes FILE_ID
```

### Output Structure
```
meet_notes_output/
└── 2025_01_19_150230/      # Simple timestamp
    ├── meeting.mp4          # Original video
    ├── audio.mp3            # Extracted audio
    ├── transcript.txt       # Raw transcription
    ├── notes.txt            # Prose-style notes
    ├── artifacts.json       # Metadata
    └── index.html           # Shareable viewer
```

### Key Improvements
1. **Single command** - No complex CLI options
2. **Prose notes** - Natural narrative, no bullets/structure
3. **HTML viewer** - All artifacts in one shareable page
4. **Simple config** - One JSON file in .credentials/
5. **Progress bar** - Clear visual feedback
6. **Smart checkpoints** - Skip expensive operations automatically

## Data Flow

### 1. Input Stage
- User provides Drive file ID/URL or selects from list
- DriveHandler downloads video to local directory

### 2. Processing Stage
- AudioProcessor extracts audio (chunks if >25MB)
- Transcriber converts to text via Whisper API
- TranscriptProcessor structures text with GPT models

### 3. Output Stage
- DocsUploader creates Google Doc
- Document shared publicly (configurable)
- URL returned to user

## File Organization

```
output/
└── dnd_sessions_YYYY_MM_DD/
    ├── <SessionName>_<ID>/
    │   ├── video.mp4           # Downloaded video
    │   ├── session_audio.mp3   # Extracted audio
    │   ├── audio_chunk_*.mp3   # Chunks (if needed)
    │   ├── transcript_*.txt    # Chunk transcripts
    │   ├── full_transcript_*.txt # Merged transcript
    │   └── processed_notes_*.txt # Final notes
    └── ...
```

## Configuration

### Environment Variables
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### Configuration Files
- `.credentials/config.json`:
  ```json
  {
    "openai_api_key": "sk-...",
    "drive_folder_id": "optional-folder-id"
  }
  ```
- `.credentials/service_account.json`: Google service account key

## Design Patterns

### 1. Pipeline Pattern
Each component transforms data for the next stage

### 2. Checkpointing
Skip completed steps on re-run:
- Check for existing audio file
- Check for existing transcript
- Always re-process and upload (for flexibility)

### 3. Error Recovery
- Comprehensive try/except blocks
- Detailed logging at each stage
- Graceful degradation

### 4. Chunk Processing
Handle API limits by splitting large files

## External Dependencies

### Python Packages
- `google-api-python-client`: Google APIs
- `google-auth`: Authentication
- `openai`: OpenAI APIs
- `pydub`: Audio processing
- `ffmpeg-python`: FFmpeg wrapper

### System Dependencies
- FFmpeg: Audio/video processing
- Python 3.9+: Required runtime

## API Integrations

### Google APIs
- **Drive API v3**: File downloads
- **Docs API v1**: Document creation
- **Authentication**: Service account with:
  - `drive.readonly`
  - `drive.file`
  - `documents`

### OpenAI APIs
- **Whisper API**: Audio transcription
  - Model: `gpt-4o-transcribe`
  - Format: `verbose_json`
- **GPT-3.5**: Transcript cleaning
- **GPT-4**: Content structuring

## Security Considerations

1. **Credentials**: All sensitive data in `.credentials/` (gitignored)
2. **Service Account**: No user interaction required
3. **Document Sharing**: Public by default (configurable)
4. **No Database**: No persistent storage of sensitive data

## Setup and Deployment Considerations

### Package Installation
When setup instructions change (e.g., new dependencies, package structure), the following locations must be updated:

1. **GitHub Actions Workflow** (`.github/workflows/tests.yml`):
   - Must include `pip install -e .` to install package in editable mode
   - Required for tests that run the package as a module (`python -m dnd_notetaker`)
   
2. **Documentation Files**:
   - `README.md`: User installation instructions
   - `Dockerfile`: Container setup instructions
   
3. **Package Configuration**:
   - `setup.py`: Package dependencies and entry points
   - `requirements.txt`: Direct dependencies
