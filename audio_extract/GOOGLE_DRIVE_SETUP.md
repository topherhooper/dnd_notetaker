# Google Drive Setup Guide

This guide explains how to set up Google Drive monitoring for the audio_extract module.

## Step 1: Get Your Google Drive Folder ID

The folder ID is the unique identifier for your Google Drive folder where Meet recordings are saved.

### How to find your folder ID:

1. **Open Google Drive** in your web browser
2. **Navigate to the folder** containing your Meet recordings
3. **Look at the URL** in your browser's address bar:
   ```
   https://drive.google.com/drive/folders/1ABC123def456GHI789jkl
                                          ^^^^^^^^^^^^^^^^^^^^^^
                                          This is your folder ID
   ```
4. **Copy the folder ID** (the long string after `/folders/`)

### Example:
- URL: `https://drive.google.com/drive/folders/1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m`
- Folder ID: `1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m`

## Step 2: Set Up Google Cloud Service Account

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Create Project" or select an existing project
3. Note your project ID

### 2.2 Enable Google Drive API

1. In the Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Drive API"
3. Click on it and press "Enable"

### 2.3 Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the details:
   - Service account name: `audio-extract-bot`
   - Service account ID: (auto-generated)
   - Description: "Service account for audio extraction from Meet recordings"
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

### 2.4 Generate Service Account Key

1. Find your service account in the credentials list
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" > "Create new key"
5. Choose "JSON" format
6. Click "Create" - this downloads the credentials file
7. **Save this file securely** - you'll need it for authentication

### 2.5 Share Your Drive Folder with the Service Account

1. Find the service account email (looks like `audio-extract-bot@your-project.iam.gserviceaccount.com`)
2. Go to your Google Drive folder with Meet recordings
3. Click the "Share" button
4. Add the service account email
5. Give it "Viewer" permissions (or "Editor" if you want to upload processed audio back)
6. Click "Send"

## Step 3: Configure audio_extract

You can provide the folder ID in several ways:

### Method 1: Configuration File (Recommended)

Create `audio_extract_config.yaml`:

```yaml
google_drive:
  service_account_file: /path/to/your-service-account-key.json
  recordings_folder_id: "1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m"  # Your folder ID here
  check_interval_seconds: 300
  days_to_look_back: 7

processing:
  output_directory: ./audio_output

monitoring:
  database_path: processed_files.db
  log_level: INFO
```

Then run:
```bash
python -m audio_extract.dev_monitor --config audio_extract_config.yaml
```

### Method 2: Environment Variables

Set environment variables:

```bash
# Linux/macOS
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json
export AUDIO_EXTRACT_FOLDER_ID=1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m
export AUDIO_EXTRACT_OUTPUT_DIR=./audio_output

# Windows (Command Prompt)
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your-service-account-key.json
set AUDIO_EXTRACT_FOLDER_ID=1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m
set AUDIO_EXTRACT_OUTPUT_DIR=.\audio_output

# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your-service-account-key.json"
$env:AUDIO_EXTRACT_FOLDER_ID="1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m"
$env:AUDIO_EXTRACT_OUTPUT_DIR=".\audio_output"
```

Then run:
```bash
python -m audio_extract.dev_monitor
```

### Method 3: Command Line Arguments

Provide directly via command line:

```bash
python -m audio_extract.dev_monitor \
  --folder-id 1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m \
  --credentials /path/to/your-service-account-key.json \
  --output ./audio_output
```

### Method 4: Programmatic Usage

In Python code:

```python
from audio_extract import Config, DriveAuth, DriveClient, DriveMonitor
from audio_extract import ProcessingTracker, AudioExtractor

# Option 1: Using config file
config = Config('audio_extract_config.yaml')
folder_id = config.get('google_drive.recordings_folder_id')

# Option 2: Direct configuration
folder_id = "1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m"  # Your folder ID

# Set up monitoring
auth = DriveAuth('/path/to/credentials.json')
client = DriveClient(auth)
tracker = ProcessingTracker('processed.db')
extractor = AudioExtractor()

monitor = DriveMonitor(
    tracker=tracker,
    extractor=extractor,
    output_dir='./audio_output',
    drive_client=client
)

# Start monitoring
monitor.monitor(folder_id, days_back=7)
```

## Step 4: Test Your Setup

1. **Test the connection:**
   ```bash
   python -m audio_extract.dev_monitor --test --folder-id YOUR_FOLDER_ID
   ```

2. **Run one check cycle:**
   ```bash
   python -m audio_extract.dev_monitor --once --folder-id YOUR_FOLDER_ID
   ```

3. **Start continuous monitoring:**
   ```bash
   python -m audio_extract.dev_monitor --folder-id YOUR_FOLDER_ID
   ```

## Troubleshooting

### "No Google credentials found"
- Check that your service account JSON file path is correct
- Ensure the GOOGLE_APPLICATION_CREDENTIALS environment variable is set
- Verify the file exists and is readable

### "Permission denied" or "File not found"
- Ensure the service account has access to your Drive folder
- Check that you shared the folder with the service account email
- Verify the folder ID is correct

### "API not enabled"
- Go to Google Cloud Console
- Enable the Google Drive API for your project

### Finding Meet Recordings
The module looks for video files with names containing:
- "meet"
- "recording"
- "meeting"
- "video"

Make sure your Meet recordings follow these naming patterns.

## Security Best Practices

1. **Store credentials securely**
   - Never commit service account keys to git
   - Use environment variables or secure key management
   - Restrict file permissions: `chmod 600 your-service-account-key.json`

2. **Use minimal permissions**
   - Only give "Viewer" access unless upload is needed
   - Create a dedicated service account for this purpose

3. **Monitor access**
   - Regularly review who has access to your Drive folders
   - Check service account activity in Google Cloud Console

## Example Configuration Files

### Minimal Configuration
```yaml
google_drive:
  recordings_folder_id: "1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m"
```

### Full Configuration
```yaml
google_drive:
  service_account_file: /home/user/.credentials/meet-audio-extract.json
  recordings_folder_id: "1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m"
  check_interval_seconds: 300  # Check every 5 minutes
  days_to_look_back: 7         # Process recordings from last 7 days
  download_temp_dir: /tmp/audio_extract

processing:
  output_directory: /home/user/extracted_audio
  delete_video_after_processing: true
  audio_format:
    bitrate: 128k
    sample_rate: 44100
    channels: 1

monitoring:
  enable_dashboard: true
  dashboard_port: 8080
  log_level: INFO
  database_path: /home/user/.audio_extract/processed.db
```

## Next Steps

Once configured:
1. Run the monitor to start processing Meet recordings
2. Check the dashboard at http://localhost:8080 to see progress
3. Find extracted audio files in your output directory
4. Review logs for any issues