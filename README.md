# DnD Session Processor

Automates the processing of DnD session recordings from Google Meet, generating structured narrative session notes and uploading them to Google Docs.

## Features

- Downloads session recordings from Gmail/Google Drive
- Automatically creates organized session directories
- Extracts audio from video recordings
- Generates transcripts using OpenAI's Whisper API
- Processes transcripts into structured narrative session notes:
  - Identifies and labels speakers (DM, players, characters)
  - Separates out-of-character discussions
  - Marks important game mechanics moments
  - Highlights memorable quotes and moments
  - Identifies session recap sections
- Uploads notes to Google Docs
- Comprehensive logging and progress tracking

## Directory Structure

The processor automatically creates an organized directory structure based on the meeting recording filename:

Input filename: `"DnD - 2025-01-10 18-41 CST - Recording.mp4"`
Creates:
```
output/
    dnd_sessions_2025_01_10/
        DnD - 2025-01-10 18-41 CST - Recording.mp4
        raw_transcript_20250110_184100.txt
        processed_notes_20250110_184100.txt
        summary_20250110_184100.json
```

## Installation

1. Clone the repository and create a virtual environment:
```bash
git clone [repository-url]
cd dnd-session-processor
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install ffmpeg (WSL/Ubuntu):
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## Configuration

1. Set up credentials directory:
```bash
mkdir .credentials
```

2. Set up Google Cloud Project:
   - Create project in Google Cloud Console
   - Enable Drive API and Docs API
   - Create OAuth 2.0 credentials
   - Download credentials and save as `.credentials/credentials.json`

3. Create `.credentials/config.json`:
```json
{
    "email": {
        "email": "your_email@gmail.com",
        "password": "your_app_specific_password",
        "imap_server": "imap.gmail.com"
    },
    "openai_api_key": "your_openai_api_key"
}
```

The `.credentials` directory will contain:
```
.credentials/
    config.json          # Your configuration
    credentials.json     # Google OAuth credentials
    token.json          # Generated OAuth token (created automatically)
```

## Usage

### Complete Pipeline

Process a DnD session recording:
```bash
# Automatic directory creation based on session date
python main.py process

# Override with custom directory
python main.py process -o custom_directory

# Keep temporary files for debugging
python main.py process --keep-temp

# Custom email subject filter
python main.py process --subject "DnD Thursday Session"
```

### Manage Temporary Files
```bash
# List temp directories
python main.py list

# Clean up old temp files (>24 hours)
python main.py clean

# Clean up with custom age
python main.py clean --age 48
```

### Individual Components

Each component can be run independently:

1. Download recording:
```bash
python email_handler.py -o output/dnd_sessions_2025_01_10
```

2. Extract audio:
```bash
python audio_processor.py -i "output/dnd_sessions_2025_01_10/DnD Session.mp4" -o output/dnd_sessions_2025_01_10
```

3. Generate transcript:
```bash
python transcriber.py -i audio.mp3 -o output/dnd_sessions_2025_01_10
```

4. Process transcript and generate notes:
```bash
# Basic processing
python transcript_processor.py -i raw_transcript.txt -o output/dnd_sessions_2025_01_10

# Analyze speakers and characters
python transcript_processor.py -i transcript.txt --analyze-speakers

# Extract game mechanics info
python transcript_processor.py -i transcript.txt --extract-mechanics
```

5. Upload to Google Docs:
```bash
python docs_uploader.py -i notes.txt -t "DnD Session - January 10th, 2025"
```

## Example Processing Flow

When you run:
```bash
python main.py process
```

The processor will:
1. Download the latest session recording from Gmail
2. Create a session directory under output/ based on the recording date
3. Extract the audio track
4. Generate a raw transcript
5. Process the transcript into structured notes
6. Upload the notes to Google Docs
7. Provide a summary with all file locations and the Google Doc URL

## Troubleshooting

1. Authentication Issues:
   - Delete `.credentials/token.json` to force re-authentication
   - Ensure APIs are enabled in Google Cloud Console
   - Check `.credentials/credentials.json` is present and valid
   - Verify permissions on `.credentials` directory

2. File Processing:
   - Verify ffmpeg installation for audio extraction
   - Check disk space for temporary files
   - Use --keep-temp for debugging

3. Directory Structure:
   - If filename parsing fails, defaults to output/session_default
   - Check file permissions if directory creation fails
   - Manually specify output directory with -o if needed

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file