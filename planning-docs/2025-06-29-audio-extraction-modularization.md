# Audio Extraction Modularization Plan

## Overview and Motivation

The audio extraction functionality is currently split between two classes in the main source directory:
- `AudioExtractor` - Simple FFmpeg-based extraction using subprocess
- `AudioProcessor` - Complex extraction with moviepy, chunking, and progress tracking

This duplication and inconsistent approaches need to be consolidated into a modular structure within the `audio_extract/` directory to improve maintainability and provide a clear interface for audio extraction operations.

## Technical Approach

### 1. Module Structure

Create the following structure in `/workspaces/dnd_notetaker/audio_extract/`:

```
audio_extract/
├── __init__.py          # Public API exports
├── extractor.py         # Core extraction logic
├── chunker.py           # Audio chunking functionality
├── tracker.py           # Track processed videos
├── utils.py             # Shared utilities (ffmpeg commands, verification)
├── exceptions.py        # Custom exceptions for audio operations
├── dev_extract.py       # Development CLI for testing extraction
├── dev_status.py        # Development CLI for checking status
├── dev_server.py        # Development web server for dashboard
├── test_integration.py  # Integration testing script
└── dashboard/           # Web dashboard for monitoring
    ├── index.html
    ├── server.py
    └── static/
        ├── style.css
        └── app.js
```

### 2. Module Responsibilities

#### `extractor.py`
- Main `AudioExtractor` class combining best of both existing implementations
- FFmpeg-based extraction (from current `AudioExtractor`)
- Progress tracking capability
- Dry-run support
- Configuration support

#### `chunker.py`
- `AudioChunker` class for splitting large audio files
- FFmpeg-based chunking (memory efficient)
- Size-based and duration-based splitting strategies
- Temporary directory management

#### `utils.py`
- FFmpeg command builders
- Audio file verification
- Duration detection using ffprobe
- File size utilities

#### `tracker.py`
- `ProcessingTracker` class for tracking processed videos
- SQLite-based storage for persistence
- Track video metadata (file path, hash, processing date, status)
- Query methods to check if video was already processed
- Support for marking failed/partial processing
- Cleanup methods for old entries

#### `exceptions.py`
- `AudioExtractionError` - Base exception
- `FFmpegNotFoundError` - FFmpeg installation issues
- `InvalidAudioFileError` - File validation failures
- `ChunkingError` - Issues during audio splitting
- `TrackingError` - Issues with the tracking database

### 3. Implementation Strategy

1. **Consolidate Core Logic**: 
   - Use FFmpeg subprocess approach (more reliable than moviepy)
   - Keep dry-run capability from `AudioExtractor`
   - Add progress tracking using FFmpeg's progress output

2. **Simplify Chunking**:
   - Remove moviepy dependency for chunking
   - Use FFmpeg directly for all operations
   - Maintain 15-minute chunk duration default

3. **Improve Error Handling**:
   - Clear exception hierarchy
   - Better error messages with recovery suggestions
   - Proper cleanup on failures

4. **Processing Tracker Features**:
   - SQLite database for lightweight, file-based storage
   - Track by file hash (MD5/SHA256) to detect moved/renamed files
   - Store processing timestamp, status, and custom metadata
   - Automatic database migrations for schema updates
   - Optional expiration of old entries to prevent DB growth

### 4. API Design

```python
# Main public API in __init__.py
from audio_extract import AudioExtractor, AudioChunker, ProcessingTracker

# Initialize tracker (creates/opens SQLite DB)
tracker = ProcessingTracker(db_path="processed_videos.db")

# Check if video was already processed
if tracker.is_processed(video_path):
    print("Video already processed, skipping...")
    metadata = tracker.get_metadata(video_path)
else:
    # Simple extraction
    extractor = AudioExtractor(config=config)
    try:
        extractor.extract(video_path, output_path)
        # Mark as successfully processed
        tracker.mark_processed(video_path, status="completed", 
                             metadata={"audio_path": output_path})
    except Exception as e:
        # Mark as failed
        tracker.mark_processed(video_path, status="failed", 
                             metadata={"error": str(e)})
        raise

# With chunking
chunker = AudioChunker(max_size_mb=25)
chunks = chunker.split(audio_path, output_dir)

# Query processing history
recent = tracker.get_recent_processed(days=7)
failed = tracker.get_failed_videos()
```

## Impact Analysis

### Files to Update
1. `/src/dnd_notetaker/audio_extractor.py` - Deprecate in favor of new module
2. `/src/dnd_notetaker/audio_processor.py` - Deprecate extraction parts
3. `/src/dnd_notetaker/meet_processor.py` - Update imports
4. `/src/dnd_notetaker/artifacts.py` - Update imports if audio extraction is used

### Files to Create
1. All files in `audio_extract/` module structure
2. Unit tests in `/tests/test_audio_extract/`
3. SQLite database file for tracking (created automatically)
4. Development tools and dashboard files

### Migration Path
1. Create new modular structure without breaking existing code
2. Update imports to use new modules
3. Remove deprecated code from main source
4. Update tests to cover new modules

## Testing Strategy

1. **Unit Tests**:
   - Test each module independently
   - Mock FFmpeg calls for fast tests
   - Test error scenarios
   - Test tracker database operations

2. **Integration Tests**:
   - Test full extraction workflow
   - Test chunking with various file sizes
   - Verify dry-run mode
   - Test processing tracker with real videos

3. **Compatibility Tests**:
   - Ensure existing code paths work with new modules
   - Test configuration compatibility

4. **Tracker-Specific Tests**:
   - Test database creation and migrations
   - Test hash-based duplicate detection
   - Test concurrent access scenarios
   - Test database cleanup and maintenance

## Development and Testing Plan

### 1. CLI Development Tools

Create development scripts in `audio_extract/` for testing:

```bash
# audio_extract/dev_extract.py - Test extraction
python -m audio_extract.dev_extract --video path/to/video.mp4 --output ./output/

# audio_extract/dev_status.py - Check processing status
python -m audio_extract.dev_status --db processed_videos.db

# audio_extract/dev_server.py - Run status dashboard
python -m audio_extract.dev_server --port 8080
```

### 2. Status Dashboard

Create a simple web dashboard (`audio_extract/dashboard/`) with:

```
dashboard/
├── index.html         # Main status page
├── static/
│   ├── style.css     # Simple styling
│   └── app.js        # Auto-refresh functionality
└── server.py         # Flask/FastAPI server
```

Dashboard features:
- **Processing Queue**: Current and pending videos
- **History Table**: Recently processed videos with status
- **Statistics**: Success rate, average processing time
- **Failed Jobs**: List of failed extractions with errors
- **Quick Actions**: Re-process failed, clear history

### 3. Development Workflow

```bash
# 1. Set up development environment
cd audio_extract/
pip install -e . --dev

# 2. Run tests on sample video
python -m audio_extract.dev_extract --video test_video.mp4 --dry-run

# 3. Start status dashboard
python -m audio_extract.dev_server

# 4. Process video and monitor in dashboard
python -m audio_extract.dev_extract --video test_video.mp4

# 5. Check processing history
python -m audio_extract.dev_status --recent 10
```

### 4. Integration Testing Script

Create `audio_extract/test_integration.py`:

```python
#!/usr/bin/env python3
"""Integration test for audio extraction pipeline"""

def test_full_pipeline():
    # 1. Initialize components
    tracker = ProcessingTracker("test.db")
    extractor = AudioExtractor()
    
    # 2. Test extraction
    print("Testing extraction...")
    
    # 3. Test chunking
    print("Testing chunking...")
    
    # 4. Verify tracking
    print("Checking tracking database...")
    
    # 5. Display results
    print("\nTest Results:")
    print("=" * 50)

if __name__ == "__main__":
    test_full_pipeline()
```

## Next Steps

1. Review and approve this plan
2. Create module structure and base classes
3. Implement development tools and dashboard
4. Migrate functionality incrementally
5. Update all imports and dependencies
6. Run comprehensive tests
7. Clean up deprecated code
