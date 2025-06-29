# Simple Interface Proposal for audio_extract

## Core Principle: Config-Driven, Minimal Commands

### 1. Primary Usage Pattern

```bash
# Development
audio-extract --config audio_extract_config.yaml.dev

# Production  
audio-extract --config audio_extract_config.prod.yaml

# That's it - it runs based on config settings
```

### 2. Essential Commands Only

```bash
# Main command - start monitoring
audio-extract --config <config-file>

# Check status (if running in background)
audio-extract status

# Stop gracefully (if running in background)
audio-extract stop

# One-time operations
audio-extract check --config <config-file>    # Run one check cycle
audio-extract test-config <config-file>       # Validate config
```

### 3. Config Controls Everything

The config file determines:
- **What**: Which folder to monitor, what files to process
- **How**: Audio format, quality, parallel processing
- **Where**: Output location, temp files, logs, database
- **When**: Check interval, retry delays, cleanup schedule
- **Behavior**: Foreground/background, logging level, error handling

### 4. Logical Defaults Built In

If not specified in config, use sensible defaults:
- Check interval: 5 minutes
- Days to look back: 7
- Audio format: MP3, 128k, mono
- Log level: INFO
- Run mode: foreground
- Retry attempts: 3

### 5. Simple Output

In foreground mode (dev):
```
[2025-06-29 10:00:00] Starting audio-extract (dev mode)
[2025-06-29 10:00:01] Connected to Drive folder: ABC123
[2025-06-29 10:00:02] Found 3 new recordings
[2025-06-29 10:00:03] Processing: meeting_2025-06-29.mp4
[2025-06-29 10:01:15] ✓ Saved: ./output/dev/meeting_2025-06-29_audio.mp3
[2025-06-29 10:01:16] Waiting 60s until next check...
```

In background mode (prod):
- Logs to file only
- Use `audio-extract status` to check
- Returns: "Running (PID: 12345) - Processed: 145/150 - Last check: 2m ago"

### 6. Questions for You

1. **Do you need the web dashboard at all?** Or is command line + logs enough?

2. **For notifications on failures**, would you prefer:
   - Just log files?
   - Webhook calls?
   - Email?
   - None - check manually?

3. **Should the tool handle its own scheduling** (like I proposed with check_interval), or would you prefer to use cron?

4. **Any other config settings** you know you'll need that I missed?

This keeps it simple: one main command, config controls everything, sensible defaults.