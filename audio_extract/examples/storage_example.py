#!/usr/bin/env python3
"""Example of using storage abstraction with audio extraction."""

import sys
from pathlib import Path
import tempfile

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_extract.storage import StorageFactory
from audio_extract.extractor import AudioExtractor


def main():
    """Demonstrate storage usage."""

    # Example 1: Local storage
    print("Example 1: Local Storage")
    print("-" * 40)

    local_config = {"type": "local", "local": {"path": "./example_output"}}

    storage = StorageFactory.create(local_config)
    print(f"Created local storage at: {storage.base_path}")

    # Create a test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test audio file (pretend it's MP3)")
        test_file = Path(f.name)

    # Save to storage
    result = storage.save(test_file, "audio/2025/01/test_audio.mp3")
    print(f"Saved to: {result['path']}")
    print(f"URL: {result['url']}")

    # Check if exists
    exists = storage.exists("audio/2025/01/test_audio.mp3")
    print(f"File exists: {exists}")

    # List files
    files = storage.list_files("audio/")
    print(f"Files in audio/: {files}")

    # Clean up
    test_file.unlink()
    storage.delete("audio/2025/01/test_audio.mp3")

    print("\n" + "=" * 60 + "\n")

    # Example 2: GCS with gcsfuse
    print("Example 2: GCS via gcsfuse (Local Mount)")
    print("-" * 40)
    print(
        """
To use GCS with gcsfuse:

1. Install gcsfuse:
   Ubuntu: sudo apt-get install gcsfuse
   macOS: brew install --cask macfuse && brew install gcsfuse

2. Mount your bucket:
   gcsfuse --implicit-dirs my-audio-bucket ~/audio-mount

3. Configure storage to use the mount:
   storage:
     type: local
     local:
       path: ~/audio-mount/audio

4. Files will be automatically synced to GCS!
"""
    )

    print("\n" + "=" * 60 + "\n")

    # Example 3: Direct GCS API
    print("Example 3: Direct GCS API")
    print("-" * 40)

    gcs_config = {
        "type": "gcs",
        "gcs": {
            "bucket_name": "my-audio-extracts",
            "credentials_path": "/path/to/service-account.json",
            "public_access": False,
            "url_expiration_hours": 24,
        },
    }

    print("GCS configuration:")
    for key, value in gcs_config["gcs"].items():
        print(f"  {key}: {value}")

    print("\nNote: To use GCS API, install: pip install google-cloud-storage")

    print("\n" + "=" * 60 + "\n")

    # Example 4: Integration with audio extraction
    print("Example 4: Full Audio Extraction with Storage")
    print("-" * 40)
    print(
        """
# In your monitor configuration:
storage:
  type: gcs  # or 'local'
  gcs:
    bucket_name: your-audio-bucket
    credentials_path: /path/to/gcs-creds.json

# The monitor will automatically:
1. Download video from Google Drive
2. Extract audio using FFmpeg
3. Upload audio to configured storage
4. Save storage URL in tracking database
5. Delete local file (optional)
"""
    )


if __name__ == "__main__":
    main()
