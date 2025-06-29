# Audio Extract Interface Design Plan

## Overview

Design a comprehensive and user-friendly interface for the audio_extract module that supports multiple interaction patterns: CLI, Web UI, API, and programmatic usage.

## User Personas & Use Cases

### 1. **Command Line User**
- Wants quick, scriptable access
- Comfortable with terminal commands
- Needs clear feedback and progress indicators
- May run in automated scripts/cron jobs

### 2. **Web Dashboard User**
- Prefers visual interface
- Wants to monitor progress in real-time
- Needs easy access to logs and statistics
- May not be technical

### 3. **Developer/Integrator**
- Needs programmatic API
- Wants to integrate into larger systems
- Requires comprehensive documentation
- Needs error handling and callbacks

### 4. **System Administrator**
- Needs monitoring and alerting
- Wants configuration management
- Requires logging and debugging tools
- Needs deployment options

## Interface Components

### 1. Command Line Interface (CLI)

#### A. Primary Commands

```bash
# Main monitoring command
audio-extract monitor [options]
  --config FILE         Configuration file path
  --folder-id ID        Google Drive folder ID
  --once               Run single check and exit
  --daemon             Run as background daemon
  --status             Show current daemon status

# Extract single file
audio-extract process [options]
  --input FILE         Video file or Drive file ID
  --output DIR         Output directory
  --format FORMAT      Audio format (mp3, wav, etc.)

# Management commands
audio-extract status    # Show processing statistics
audio-extract history   # Show recent processing history
audio-extract retry     # Retry failed extractions
audio-extract clean     # Clean up old records
```

#### B. Interactive CLI Mode

```bash
$ audio-extract interactive

Audio Extract v0.1.0
Type 'help' for available commands.

audio> connect folder-id-123
✓ Connected to Google Drive folder

audio> status
📊 Statistics:
  Total processed: 145
  Success rate: 96.5%
  Last check: 2 minutes ago
  
audio> monitor start
▶️  Starting continuous monitoring...
[2025-06-29 10:00:00] Found 3 new recordings
[2025-06-29 10:00:15] Processing: meeting_2025-06-29.mp4
[2025-06-29 10:01:30] ✓ Extracted: meeting_2025-06-29_audio.mp3

audio> monitor stop
⏸️  Monitoring paused
```

### 2. Web Dashboard Interface

#### A. Main Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│ 🎵 Audio Extract Dashboard                    [Status: Active]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │   Active    │ │  Processed  │ │   Success   │           │
│ │     ✓       │ │    1,234    │ │   98.5%     │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                             │
│ Recent Activity                              [Refresh] [▼]  │
│ ┌─────────────────────────────────────────────────────────┤
│ │ 10:15 ✓ meeting_2025-06-29.mp4 → audio extracted       │
│ │ 10:10 ✓ standup_recording.mp4 → audio extracted        │
│ │ 09:45 ⚠ team_sync.mp4 → retrying (network error)       │
│ │ 09:30 ✓ project_review.mp4 → audio extracted           │
│ └─────────────────────────────────────────────────────────┤
│                                                             │
│ [▶️ Start] [⏸️ Pause] [🔄 Check Now] [⚙️ Settings]          │
└─────────────────────────────────────────────────────────────┘
```

#### B. Settings Page
```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Settings                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Google Drive Configuration                                  │
│ ┌─────────────────────────────────────────────────────────┤
│ │ Folder ID: [1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m    ]      │
│ │ Check Interval: [300] seconds                           │
│ │ Days to Look Back: [7]                                  │
│ └─────────────────────────────────────────────────────────┤
│                                                             │
│ Audio Settings                                              │
│ ┌─────────────────────────────────────────────────────────┤
│ │ Format: [MP3 ▼]  Bitrate: [128k ▼]                     │
│ │ Channels: (•) Mono ( ) Stereo                           │
│ └─────────────────────────────────────────────────────────┤
│                                                             │
│ [💾 Save] [❌ Cancel] [📤 Export Config]                    │
└─────────────────────────────────────────────────────────────┘
```

### 3. REST API Interface

#### A. Endpoints

```yaml
# Status & Monitoring
GET  /api/status              # System status
GET  /api/stats               # Processing statistics
GET  /api/history             # Processing history
POST /api/monitor/start       # Start monitoring
POST /api/monitor/stop        # Stop monitoring
GET  /api/monitor/status      # Monitoring status

# Processing
POST /api/process             # Process single file
GET  /api/process/{job_id}    # Get job status
POST /api/retry/{job_id}      # Retry failed job

# Configuration
GET  /api/config              # Get current config
PUT  /api/config              # Update config
POST /api/config/validate     # Validate config

# WebSocket
WS   /api/ws                  # Real-time updates
```

#### B. API Response Format

```json
{
  "status": "success",
  "data": {
    "processed": 145,
    "success_rate": 96.5,
    "last_check": "2025-06-29T10:00:00Z"
  },
  "meta": {
    "version": "0.1.0",
    "timestamp": "2025-06-29T10:15:00Z"
  }
}
```

### 4. Configuration Interface

#### A. YAML Configuration
```yaml
# audio_extract_config.yaml
version: "1.0"

google_drive:
  folder_id: "${DRIVE_FOLDER_ID}"  # Environment variable support
  credentials: !include credentials.json  # File inclusion
  check_interval: 5m  # Human-readable durations
  
audio:
  format: mp3
  quality: high  # Presets: low, medium, high, custom
  custom_settings:
    bitrate: 192k
    sample_rate: 48000
    
monitoring:
  notifications:
    email:
      enabled: true
      recipients: 
        - admin@example.com
      on_failure: true
      on_success: false
    webhook:
      url: https://example.com/webhook
      events: [failure, completion]
      
advanced:
  parallel_downloads: 3
  retry_attempts: 3
  retry_delay: 30s
```

#### B. Environment Configuration
```bash
# .env file
AUDIO_EXTRACT_MODE=production
AUDIO_EXTRACT_LOG_LEVEL=info
AUDIO_EXTRACT_FOLDER_ID=1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m
AUDIO_EXTRACT_WEBHOOK_SECRET=secret123
```

### 5. Programmatic Interface

#### A. High-Level API
```python
from audio_extract import AudioExtractService

# Simple usage
service = AudioExtractService.from_config('config.yaml')
service.start_monitoring()

# With callbacks
def on_file_processed(file_info):
    print(f"Processed: {file_info.name}")
    
service = AudioExtractService(
    folder_id='123',
    on_processed=on_file_processed,
    on_error=lambda e: logger.error(e)
)

# Async support
async with AudioExtractService() as service:
    await service.monitor_async()
```

#### B. Plugin System
```python
from audio_extract import Plugin

class CustomNotifier(Plugin):
    def on_extraction_complete(self, file_info, audio_path):
        # Send custom notification
        send_slack_message(f"Processed: {file_info.name}")
        
    def on_error(self, error, file_info):
        # Handle errors
        log_to_sentry(error)

# Register plugin
service.register_plugin(CustomNotifier())
```

## User Experience Enhancements

### 1. Progress Indicators
- Real-time progress bars for downloads
- ETA calculations
- Processing queue visualization

### 2. Error Handling
- Clear error messages with suggested fixes
- Automatic retry with exponential backoff
- Error categorization (network, permissions, format)

### 3. Notifications
- Desktop notifications (optional)
- Email summaries
- Webhook integrations
- Mobile app push notifications (future)

### 4. Logging & Debugging
- Structured logging with levels
- Log rotation and archival
- Debug mode with verbose output
- Performance metrics

## Implementation Priorities

### Phase 1: Core CLI Enhancement
1. Improve existing CLI commands
2. Add interactive mode
3. Better progress indicators
4. Configuration validation

### Phase 2: Web Dashboard
1. Basic dashboard with statistics
2. Real-time updates via WebSocket
3. Settings management UI
4. Processing history view

### Phase 3: API & Integration
1. REST API implementation
2. WebSocket for real-time updates
3. Plugin system
4. Webhook support

### Phase 4: Advanced Features
1. Multi-folder support
2. Scheduling system
3. Advanced filtering rules
4. Performance optimizations

## Technical Considerations

### 1. Architecture
- Separate concerns: Core, CLI, Web, API
- Event-driven architecture
- Queue-based processing
- Microservice-ready design

### 2. Dependencies
- Click or Typer for CLI
- FastAPI for web/API
- Vue.js or React for dashboard
- Socket.IO for real-time updates

### 3. Deployment
- Docker support
- SystemD service files
- PM2 configuration
- Kubernetes manifests

### 4. Security
- API authentication (JWT/OAuth)
- Rate limiting
- Input validation
- Secure credential storage

## Success Metrics

1. **Usability**
   - Time to first successful extraction < 5 minutes
   - Configuration errors < 5%
   - User satisfaction > 90%

2. **Performance**
   - Processing throughput > 10 files/minute
   - API response time < 100ms
   - Dashboard load time < 2 seconds

3. **Reliability**
   - Uptime > 99.9%
   - Successful extraction rate > 95%
   - Automatic recovery from failures

## Next Steps

1. Review and refine interface design
2. Create mockups for web dashboard
3. Define API specification (OpenAPI)
4. Build CLI interactive mode prototype
5. Implement core event system
6. Develop plugin architecture