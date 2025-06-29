# Google Drive Monitoring Integration Plan

## Overview and Motivation

The audio_extract module currently only handles local files, but the original purpose is to monitor a Google Drive folder where Google Meet recordings are automatically saved. We need to integrate Google Drive monitoring capabilities to continuously check for new recordings and automatically process them.

## Current State Analysis

### What We Have:
1. **audio_extract module** - Fully functional for local files
   - AudioExtractor for extraction
   - ProcessingTracker for tracking what's been processed
   - Web dashboard for monitoring status

2. **Main project** has Google Drive integration:
   - `/src/dnd_notetaker/drive_handler.py` - Google Drive API wrapper
   - `/src/dnd_notetaker/simplified_drive_handler.py` - Simplified version
   - Service account authentication support

### What's Missing:
1. Drive monitoring loop that checks for new recordings
2. Integration between Drive API and audio extraction
3. Automatic downloading and processing pipeline
4. Configuration for monitoring settings
5. Background service capability

## Technical Approach

### 1. Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Drive                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Meet Recordings Folder                        │   │
│  │  • recording_2025-06-29_10-00.mp4                  │   │
│  │  • recording_2025-06-29_14-30.mp4 (new)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Monitor & Download
┌─────────────────────────────────────────────────────────────┐
│                  Drive Monitor Service                       │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │  Drive Handler  │───▶│ Monitor Loop    │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Download Video  │    │ Check Tracker   │               │
│  └─────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Process
┌─────────────────────────────────────────────────────────────┐
│                   Audio Extract Module                       │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Audio Extractor │───▶│    Tracker      │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │  Audio Files    │    │  Dashboard      │               │
│  └─────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Component Design

#### A. Configuration System
```python
# config.yaml or config.json
{
    "google_drive": {
        "service_account_file": "path/to/service_account.json",
        "recordings_folder_id": "1234567890abcdef",
        "check_interval_seconds": 300,  # 5 minutes
        "days_to_look_back": 7
    },
    "processing": {
        "output_directory": "./audio_output",
        "upload_audio_to_drive": true,
        "delete_local_video_after_processing": true,
        "audio_format": {
            "bitrate": "128k",
            "sample_rate": 44100
        }
    },
    "monitoring": {
        "enable_dashboard": true,
        "dashboard_port": 8080,
        "log_level": "INFO"
    }
}
```

#### B. Drive Monitor Service
- Runs as a long-running process or daemon
- Periodically checks Google Drive folder
- Downloads new recordings
- Triggers audio extraction
- Updates tracking database
- Optionally uploads audio back to Drive

#### C. CLI Integration
```bash
# Start monitoring service
python -m audio_extract.monitor --config config.yaml

# One-time sync
python -m audio_extract.sync --folder-id FOLDER_ID --days-back 7

# Check monitoring status
python -m audio_extract.monitor-status
```

### 3. Implementation Plan

#### Phase 1: Core Integration
1. Create configuration system
2. Adapt/import Drive handler from main project
3. Create DriveMonitor class
4. Integrate with ProcessingTracker

#### Phase 2: Service Implementation
1. Create monitoring service script
2. Add daemon/background mode support
3. Implement graceful shutdown
4. Add logging and error handling

#### Phase 3: Enhanced Features
1. Update dashboard to show Drive sync status
2. Add email notifications for failures
3. Support for multiple Drive folders
4. Batch processing optimization

## Implementation Strategy

### 1. Self-Contained Drive Integration

Since we want to keep everything within the audio_extract package, we will:

1. **Create our own Drive handler** within audio_extract
   - Minimal implementation focused on our specific needs
   - Only the features needed for monitoring and downloading
   - Service account authentication support

2. **Add required dependencies** to requirements.txt:
   ```
   google-api-python-client>=2.0.0
   google-auth>=2.0.0
   google-auth-httplib2>=0.1.0
   ```

3. **Module structure** will be:
   ```
   audio_extract/
   ├── drive/
   │   ├── __init__.py
   │   ├── client.py         # Google Drive API client
   │   ├── monitor.py        # Monitoring logic
   │   └── auth.py          # Authentication helpers
   ├── config.py            # Configuration management
   └── cli/
       ├── __init__.py
       └── monitor.py       # CLI for monitoring
   ```

### 2. Database Schema Updates

Add tables for Drive-specific tracking:
```sql
CREATE TABLE drive_files (
    id INTEGER PRIMARY KEY,
    file_id TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    folder_id TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    modified_time TIMESTAMP,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    folder_id TEXT,
    files_found INTEGER,
    files_processed INTEGER,
    files_failed INTEGER,
    duration_seconds REAL
);
```

## Testing Strategy

### 1. Unit Tests
- Mock Google Drive API calls
- Test monitoring logic
- Test configuration loading
- Test error scenarios

### 2. Integration Tests
- Use test Drive folder
- Test full download → extract → track flow
- Test recovery from interruptions

### 3. Manual Testing Checklist
- [ ] Monitor detects new files
- [ ] Already processed files are skipped
- [ ] Failed downloads are retried
- [ ] Dashboard shows Drive sync status
- [ ] Service handles network interruptions
- [ ] Graceful shutdown works

## Security Considerations

1. **Service Account Credentials**
   - Store securely (not in git)
   - Use environment variables option
   - Rotate regularly

2. **File Access**
   - Validate file types before processing
   - Limit folder access scope
   - Sanitize file names

3. **Resource Limits**
   - Maximum file size limits
   - Concurrent download limits
   - Disk space monitoring

## Performance Considerations

1. **Efficient Checking**
   - Use Drive API's modifiedTime filter
   - Cache folder structure
   - Batch API requests

2. **Download Optimization**
   - Stream large files
   - Resume interrupted downloads
   - Parallel processing option

3. **Resource Management**
   - Clean up temporary files
   - Monitor disk usage
   - Rate limit API calls

## Future Enhancements

1. **Advanced Monitoring**
   - Watch for real-time changes (webhooks)
   - Support for shared drives
   - Multi-account support

2. **Processing Pipeline**
   - Transcription integration
   - Note generation
   - Automatic summarization

3. **Deployment Options**
   - Docker container
   - Cloud Functions
   - Kubernetes CronJob

## Next Steps

1. Review and approve this plan
2. Decide on import strategy (Option A/B/C)
3. Create configuration schema
4. Implement DriveMonitor class
5. Create monitoring service
6. Update documentation
7. Test with real Meet recordings