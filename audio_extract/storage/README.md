# Storage Module

The storage module provides a flexible abstraction for storing extracted audio files, supporting both local file system and Google Cloud Storage (GCS).

## Features

- **Storage Abstraction**: Common interface for different storage backends
- **Local Storage**: Simple file system storage
- **GCS Storage**: Direct Google Cloud Storage integration
- **gcsfuse Support**: Use GCS through local mount (recommended for development)
- **Automatic Organization**: Files organized by year/month
- **URL Generation**: Get access URLs (file:// or https://)

## Quick Start

### Local Storage

```python
from audio_extract.storage import StorageFactory

config = {
    'type': 'local',
    'local': {
        'path': './output/audio'
    }
}

storage = StorageFactory.create(config)
storage.save(local_file, "audio/2025/01/meeting.mp3")
```

### GCS with gcsfuse (Recommended for Development)

1. Install gcsfuse:
```bash
# Ubuntu/Debian
sudo apt-get install gcsfuse

# macOS
brew install --cask macfuse
brew install gcsfuse
```

2. Mount your bucket:
```bash
gcsfuse --implicit-dirs my-audio-bucket ~/audio-mount
```

3. Use local storage pointing to mount:
```yaml
storage:
  type: local
  local:
    path: ~/audio-mount/audio
```

### Direct GCS API

```yaml
storage:
  type: gcs
  gcs:
    bucket_name: my-audio-extracts
    credentials_path: /path/to/service-account.json
    public_access: false
    url_expiration_hours: 24
```

## Configuration

### In `audio_extract_config.yaml`:

```yaml
# For development with local storage
storage:
  type: local
  local:
    path: ./output/dev

# For production with GCS
storage:
  type: gcs
  gcs:
    bucket_name: ${GCS_BUCKET_NAME}
    credentials_path: ${GCS_CREDENTIALS_PATH}
    public_access: false
    url_expiration_hours: 168  # 1 week
```

## Storage Adapters

### LocalStorageAdapter

- Stores files on local file system
- Returns `file://` URLs
- No external dependencies
- Good for development and testing

### GCSStorageAdapter

- Stores files in Google Cloud Storage
- Returns public URLs or signed URLs
- Requires `google-cloud-storage` package
- Supports service account authentication

## Integration with Audio Extract

The storage module is automatically integrated with the Drive monitor:

1. When a new recording is found, it's downloaded from Google Drive
2. Audio is extracted using FFmpeg
3. The audio file is uploaded to configured storage
4. Storage URL is saved in the tracking database
5. Local file is optionally deleted

## Testing

Run storage tests:
```bash
pytest tests/test_storage.py -v
```

## Security Considerations

- Store GCS credentials securely (not in version control)
- Use signed URLs for private content
- Set appropriate bucket permissions
- Enable audit logging for production

## Performance Tips

- Use gcsfuse for development (simpler, no code changes)
- Use direct GCS API for production (better performance)
- Enable parallel uploads for multiple files
- Consider regional buckets for lower latency