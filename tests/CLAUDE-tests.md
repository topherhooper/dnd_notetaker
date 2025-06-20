# CLAUDE-tests.md

This file documents all test scripts in the tests/ directory. Claude Code is responsible for maintaining this file as tests are created, modified, or removed.

## Testing Framework

- **Framework**: pytest
- **Mocking**: unittest.mock
- **Coverage**: pytest-cov
- **Python**: 3.9+ required

## Test Files Overview

### conftest.py
**Purpose**: Shared test fixtures and configuration

**Fixtures**:
- `temp_dir`: Creates temporary directory for test isolation
- `sample_video`: Creates a minimal test video file
- `sample_audio`: Creates a test audio file
- `sample_transcript`: Provides sample transcript text
- `mock_drive_service`: Mocked Google Drive service
- `mock_docs_service`: Mocked Google Docs service

### test_meet_notes.py (NEW)
**Purpose**: Tests the simplified meet_notes entry point

**Test Classes**:
- `TestMeetNotes`

**Key Test Scenarios**:
- `test_main_no_args`: Processing with no arguments (most recent)
- `test_main_with_file_id`: Processing with specific file ID
- `test_main_handles_errors`: General error handling

**Mocked Dependencies**:
- Config and MeetProcessor classes
- System argv for CLI arguments

### test_config.py (NEW)
**Purpose**: Tests simplified configuration management

**Test Classes**:
- `TestConfig`

**Key Test Scenarios**:
- `test_load_existing_config`: Loading existing config file
- `test_create_default_config`: Default config creation
- `test_openai_api_key_property`: API key access
- `test_service_account_path_property`: Service account validation
- `test_output_dir_property`: Output directory creation

**Mocked Dependencies**:
- File system operations
- Environment variables

### test_meet_processor.py (NEW)
**Purpose**: Tests the main processing orchestrator

**Test Classes**:
- `TestMeetProcessor`

**Key Test Scenarios**:
- `test_init`: Component initialization
- `test_process_full_pipeline`: End-to-end processing
- `test_process_with_file_id`: Specific file processing
- `test_checkpointing_skips_existing_audio`: Audio checkpoint
- `test_checkpointing_skips_existing_transcript`: Transcript checkpoint
- `test_notes_always_regenerated`: Notes regeneration

**Mocked Dependencies**:
- All processing components
- Progress bar (tqdm)

### test_audio_extractor.py (NEW)
**Purpose**: Tests simplified audio extraction

**Test Classes**:
- `TestAudioExtractor`

**Key Test Scenarios**:
- `test_extract_success`: Successful extraction
- `test_extract_ffmpeg_error`: FFmpeg error handling
- `test_extract_ffmpeg_not_found`: Missing FFmpeg
- `test_extract_output_not_created`: Output verification
- `test_extract_creates_output_directory`: Directory creation

**Mocked Dependencies**:
- FFmpeg subprocess
- File system

### test_note_generator.py (NEW)
**Purpose**: Tests prose-style note generation

**Test Classes**:
- `TestNoteGenerator`

**Key Test Scenarios**:
- `test_generate_single_chunk`: Short transcript processing
- `test_generate_multiple_chunks`: Long transcript chunking
- `test_split_transcript`: Chunking logic
- `test_prose_style_requirements`: Prose format verification
- `test_generate_notes_error_handling`: API error handling

**Mocked Dependencies**:
- OpenAI API client
- Chat completions

### test_artifacts.py (NEW)
**Purpose**: Tests artifact management and sharing

**Test Classes**:
- `TestArtifacts`

**Key Test Scenarios**:
- `test_create_share_bundle`: Bundle creation
- `test_file_metadata`: Metadata recording
- `test_get_file_size_formatting`: Size formatting
- `test_html_viewer_content`: HTML generation
- `test_html_viewer_styling`: CSS styling

**Mocked Dependencies**:
- File system operations

### test_simplified_drive_handler.py (NEW)
**Purpose**: Tests simplified Google Drive operations

**Test Classes**:
- `TestSimplifiedDriveHandler`

**Key Test Scenarios**:
- `test_download_file_success`: File download
- `test_download_file_not_video`: Video validation
- `test_download_most_recent_success`: Recent file selection
- `test_download_most_recent_no_videos`: No files handling
- `test_format_size`: Size formatting

**Mocked Dependencies**:
- Google Drive API
- Service account credentials

### test_audio_processor.py
**Purpose**: Tests audio extraction and chunking functionality

**Test Classes**:
- `TestAudioProcessor`

**Key Test Scenarios**:
- `test_extract_audio`: Successful audio extraction from video
- `test_extract_audio_file_not_found`: Missing input file handling
- `test_chunk_audio`: Large file chunking (>25MB)
- `test_chunk_audio_small_file`: Small file bypass
- `test_get_audio_duration`: Duration calculation

**Mocked Dependencies**:
- FFmpeg subprocess calls
- File system operations

### test_docs_uploader.py
**Purpose**: Tests Google Docs creation and sharing

**Test Classes**:
- `TestDocsUploader`

**Key Test Scenarios**:
- `test_upload_notes`: Successful document creation
- `test_upload_notes_with_public_share`: Public sharing enabled
- `test_upload_notes_no_public_share`: Public sharing disabled
- `test_upload_notes_api_error`: API failure handling

**Mocked Dependencies**:
- Google Docs API
- Authentication services

### test_drive_handler.py
**Purpose**: Tests Google Drive file downloads

**Test Classes**:
- `TestDriveHandler`

**Key Test Scenarios**:
- `test_download_file`: Successful file download
- `test_download_file_not_found`: Missing file handling
- `test_get_shared_items`: List shared files
- `test_parse_drive_url`: URL parsing variants

**Mocked Dependencies**:
- Google Drive API
- File download operations

### test_main.py
**Purpose**: Tests main orchestration and CLI functionality

**Test Classes**:
- `TestMeetingProcessor`

**Key Test Scenarios**:
- `test_process_full_pipeline`: End-to-end processing
- `test_process_with_existing_files`: Checkpoint skip logic
- `test_interactive_mode`: User interaction flow
- `test_list_sessions`: Directory listing
- `test_clean_sessions`: Cleanup functionality
- `test_cli_process_command`: CLI argument parsing
- `test_cli_error_handling`: Invalid command handling

**Mocked Dependencies**:
- All component classes
- User input
- File system

### test_setup_credentials.py
**Purpose**: Tests credential setup and validation

**Test Functions**:
- `test_get_google_credentials_url`: URL generation
- `test_create_credentials_directory`: Directory creation
- `test_save_service_account_json`: Secure file saving
- `test_save_config_json`: Config file creation
- `test_check_permissions`: File permission validation

**Key Test Scenarios**:
- Directory creation with proper permissions (700)
- File saving with secure permissions (600)
- Invalid JSON handling
- Permission verification

### test_transcriber.py
**Purpose**: Tests audio transcription functionality

**Test Classes**:
- `TestTranscriber`

**Key Test Scenarios**:
- `test_transcribe_audio`: Single file transcription
- `test_transcribe_chunked_audio`: Multi-chunk processing
- `test_merge_transcripts`: Transcript combination
- `test_transcribe_audio_api_error`: API failure handling

**Mocked Dependencies**:
- OpenAI Whisper API
- File operations

### test_utils.py
**Purpose**: Tests utility functions

**Test Functions**:
- `test_setup_logging`: Logger configuration
- `test_load_config`: Config file loading
- `test_get_timestamp`: Timestamp generation
- `test_clean_filename`: Filename sanitization
- `test_save_to_file`: File writing
- `test_format_duration`: Time formatting
- `test_clean_old_directories`: Directory cleanup

**Key Test Scenarios**:
- Logging setup with different levels
- Missing config file handling
- Invalid character removal
- Age-based cleanup logic

## Test Patterns

### 1. Mocking Strategy
- Mock all external API calls
- Mock file system operations when testing logic
- Use real temp files for integration tests

### 2. Test Isolation
- Each test creates its own temp directory
- Cleanup in teardown methods
- No shared state between tests

### 3. Error Testing
- Test both success and failure paths
- Verify error messages and logging
- Check graceful degradation

### 4. Integration Testing
- `test_main.py` tests full pipeline
- Verifies component interaction
- Checks checkpoint behavior

## Coverage Areas

### Well Covered
- Happy path scenarios
- Basic error handling
- API mocking
- File operations
- CLI functionality

### Needs Additional Testing
- Network timeout scenarios
- Concurrent processing
- Large file edge cases
- Authentication token refresh
- Partial failure recovery
- Cross-platform compatibility

## Running Tests

### Basic Test Run
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dnd_notetaker --cov-report=html

# Run specific test file
pytest tests/test_audio_processor.py

# Run specific test
pytest tests/test_main.py::TestMeetingProcessor::test_process_full_pipeline

# Verbose output
pytest -v

# Show print statements
pytest -s
```

### Coverage Report
```bash
# Generate HTML coverage report
pytest --cov=dnd_notetaker --cov-report=html
# Open htmlcov/index.html in browser

# Terminal coverage summary
pytest --cov=dnd_notetaker --cov-report=term-missing
```

## Adding New Tests

When adding new functionality:
1. Create test file if new module: `test_<module_name>.py`
2. Follow existing patterns for mocking
3. Test both success and error cases
4. Update this documentation
5. Run full test suite before committing

## Test Data

Sample test data is created by fixtures in `conftest.py`:
- Video files: 1-second minimal MP4
- Audio files: Silent MP3
- Transcripts: Lorem ipsum text
- Config files: Minimal valid JSON

## Known Test Issues

1. **FFmpeg Dependency**: Some tests require FFmpeg installed
2. **Temp File Cleanup**: Occasionally leaves artifacts on test failure
3. **Mock Complexity**: Google API mocks can be verbose
4. **Platform Differences**: File permissions tests may vary on Windows