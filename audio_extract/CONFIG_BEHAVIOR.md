# Config-Driven Behavior Summary

## Development Mode

```bash
audio-extract --config audio_extract_config.yaml.dev
```

**What happens:**
1. Runs in foreground - you see all output in terminal
2. Opens web dashboard automatically at http://localhost:8080
3. Shows DEBUG level logs in console
4. **On any error: EXITS immediately and shows full traceback**
5. Does NOT retry failed files
6. Keeps downloaded videos for debugging

**Example output:**
```
[2025-06-29 10:00:00] Starting audio-extract (development)
[2025-06-29 10:00:00] Web dashboard: http://localhost:8080
[2025-06-29 10:00:01] Connected to Drive folder: dev-folder-123
[2025-06-29 10:00:02] Found 1 new recording
[2025-06-29 10:00:03] Downloading: meeting_2025-06-29.mp4
[2025-06-29 10:00:45] ERROR: Failed to extract audio
Traceback (most recent call last):
  File "extractor.py", line 45, in extract
    ...
FFmpegError: Invalid codec parameters

Exiting due to error (stop_on_error=true)
```

## Production Mode

```bash
audio-extract --config audio_extract_config.prod.yaml
```

**What happens:**
1. Runs in background as daemon
2. NO web dashboard
3. Logs to file only (/var/log/audio-extract/)
4. **On any error: Sends email and continues running**
5. Retries failed files up to 3 times
6. Deletes videos after processing to save space

**Email on failure:**
```
Subject: [audio-extract] Processing Failed

Failed to process: meeting_2025-06-29.mp4
Error: Network timeout downloading file
Time: 2025-06-29 10:00:45 UTC
Host: prod-server-01

This was attempt 1 of 3. Will retry in 5 minutes.

View logs: /var/log/audio-extract/audio-extract.log
```

## Key Differences

| Feature | Dev | Prod |
|---------|-----|------|
| Run mode | Foreground (see output) | Background (daemon) |
| Web dashboard | Yes (auto-opens) | No |
| On error | Exit immediately | Email & continue |
| Retry failures | No | Yes (3 times) |
| Keep video files | Yes | No (delete after) |
| Check interval | 60 seconds | 5 minutes |
| Log level | DEBUG | INFO |

## Environment Variables

**Development:** Usually none needed

**Production:** 
```bash
# Required for email notifications
export SMTP_HOST=smtp.gmail.com
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export ALERT_EMAIL=ops-team@example.com

# Required for Drive
export AUDIO_EXTRACT_FOLDER_ID=prod-folder-id-789
```