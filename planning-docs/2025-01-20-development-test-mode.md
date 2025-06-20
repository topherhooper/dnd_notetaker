# Dry Run Feature

**Core Goal**: Add a `--dry-run` flag to show what operations would be performed without executing them. No other features or complexity.

## Overview and Motivation

Users often want to see what operations the dnd_notetaker will perform before actually executing them. This is especially useful when:
- Testing configuration changes
- Understanding the processing pipeline
- Avoiding accidental operations on production files
- Debugging issues without running expensive operations

The `--dry-run` flag allows users to run the full command and see what would happen without actually:
- Downloading files from Google Drive
- Running FFmpeg to extract audio
- Making OpenAI API calls
- Creating output files

## Technical Approach

### 1. Command-Line Flag

Add a single new flag to `meet_notes.py`:

```python
parser.add_argument('--dry-run', action='store_true',
                    help='Show what would happen without executing operations')
```

### 2. Implementation Strategy

Pass the dry_run flag through the configuration and check it before each expensive operation:

```python
# In Config class
class Config:
    def __init__(self, config_path=None, dry_run=False):
        self.dry_run = dry_run
        # ... existing config loading ...

# In MeetProcessor
def process(self, file_id):
    if self.config.dry_run:
        print(f"[DRY RUN] Would download file {file_id} from Google Drive")
    else:
        self.download_file(file_id)
    
    if self.config.dry_run:
        print(f"[DRY RUN] Would extract audio using FFmpeg")
    else:
        self.extract_audio()
    
    # ... etc for each operation
```

### 3. Detailed Logging

When in dry-run mode, provide detailed information about what would happen:

```python
def download_file(self, file_id, output_path):
    if self.config.dry_run:
        print(f"[DRY RUN] Would download Google Drive file:")
        print(f"  File ID: {file_id}")
        print(f"  Output path: {output_path}")
        print(f"  Estimated size: Unknown (would query Drive API)")
        return output_path  # Return path for pipeline continuation
    else:
        # Actual download implementation
        return self.drive_handler.download_file(file_id, output_path)
```

### 4. Component Updates

Each component needs to check the dry_run flag. Note: Components should access dry_run through their passed config object, not as a direct parameter.

#### SimplifiedDriveHandler
```python
def download_file(self, file_id, output_path):
    if self.config.dry_run:
        print(f"[DRY RUN] Would download from Google Drive:")
        print(f"  File ID: {file_id}")
        print(f"  Destination: {output_path}")
        return output_path
    # ... actual implementation
```

#### AudioExtractor
```python
def extract_audio(self, video_path, output_path):
    if self.config.dry_run:
        print(f"[DRY RUN] Would extract audio using FFmpeg:")
        print(f"  Input: {video_path}")
        print(f"  Output: {output_path}")
        print(f"  Command: ffmpeg -i {video_path} -vn -acodec libmp3lame {output_path}")
        return output_path
    # ... actual implementation
```

#### Transcriber
```python
def transcribe(self, audio_path):
    if self.config.dry_run:
        print(f"[DRY RUN] Would transcribe audio using OpenAI Whisper:")
        print(f"  Audio file: {audio_path}")
        print(f"  Model: gpt-4o-transcribe")
        print(f"  Estimated cost: ~$0.006 per minute")
        return {"text": "[DRY RUN - No actual transcript]"}
    # ... actual implementation
```

#### NoteGenerator
```python
def generate_notes(self, transcript):
    if self.config.dry_run:
        print(f"[DRY RUN] Would generate notes using OpenAI GPT:")
        print(f"  Model: gpt-4-turbo-preview")
        print(f"  Transcript length: {len(transcript.get('text', ''))} characters")
        print(f"  Estimated tokens: ~{len(transcript.get('text', '')) // 4}")
        return "[DRY RUN - No actual notes generated]"
    # ... actual implementation
```

## Impact Analysis

### Benefits

1. **No External Dependencies**: Users can test without credentials or network access
2. **Cost Savings**: No API calls means no charges during testing
3. **Fast Feedback**: Instant validation of configuration and flow
4. **Safe Testing**: No risk of accidental operations on production data
5. **Debugging Aid**: Clear visibility into what operations would occur

### Changes Required

1. Add `--dry-run` flag to command-line parser
2. Pass dry_run through Config class
3. Add dry_run checks in each component
4. Ensure components return appropriate dummy values in dry-run mode
5. Add informative logging for dry-run operations

### Backward Compatibility

- All changes are additive
- Default behavior unchanged (dry_run=False)
- No impact on existing configurations or workflows

## Testing Strategy

### Unit Tests

Each component should have unit tests to verify dry-run behavior:

#### Config Tests (`test_config.py`)
```python
def test_config_dry_run_flag():
    """Test that Config properly stores dry_run flag"""
    config = Config(dry_run=True)
    assert config.dry_run is True
    
    config = Config(dry_run=False)
    assert config.dry_run is False

def test_config_dry_run_with_file():
    """Test that dry_run flag works with config file"""
    config = Config(config_path="test_config.json", dry_run=True)
    assert config.dry_run is True  # CLI flag should override
```

#### Component Tests
Each component needs tests to verify:
1. No external calls are made when dry_run=True
2. Appropriate mock data is returned
3. Correct log messages are printed

Example for `test_simplified_drive_handler.py`:
```python
def test_download_file_dry_run(mock_print, mock_service):
    """Test that download_file respects dry_run flag"""
    handler = SimplifiedDriveHandler(config=Config(dry_run=True))
    result = handler.download_file("ABC123", "/tmp/output.mp4")
    
    # Should return the output path without downloading
    assert result == "/tmp/output.mp4"
    
    # Should not make any API calls
    mock_service.assert_not_called()
    
    # Should print dry-run message
    mock_print.assert_called_with("[DRY RUN] Would download from Google Drive:")
```

### Integration Tests

Full pipeline tests to ensure dry-run works end-to-end:

```python
def test_full_pipeline_dry_run(tmp_path, capsys):
    """Test complete pipeline in dry-run mode"""
    # Run with dry-run flag
    result = subprocess.run([
        sys.executable, "-m", "dnd_notetaker", 
        "TEST_FILE_ID", "--dry-run",
        "--output-dir", str(tmp_path)
    ], capture_output=True, text=True)
    
    # Should complete successfully
    assert result.returncode == 0
    
    # Verify output contains all expected dry-run messages
    output = result.stdout
    assert "[DRY RUN] Would download Google Drive file:" in output
    assert "[DRY RUN] Would extract audio using FFmpeg:" in output
    assert "[DRY RUN] Would transcribe audio using OpenAI Whisper:" in output
    assert "[DRY RUN] Would generate notes using OpenAI GPT:" in output
    
    # Verify no files were created
    assert len(list(tmp_path.iterdir())) == 0
    
    # Verify no external calls were made (no credentials needed)
    assert "Error" not in output
    assert "Exception" not in output
```

### Verification Steps

1. **No Side Effects Verification**
   ```bash
   # Run with non-existent credentials
   rm -rf ~/.config/gcloud
   unset OPENAI_API_KEY
   python -m dnd_notetaker FILE_ID --dry-run
   # Should complete without errors
   ```

2. **Output Validation**
   ```bash
   # Capture output and verify format
   python -m dnd_notetaker FILE_ID --dry-run 2>&1 | tee dry_run_output.log
   
   # Check for required elements
   grep -q "\[DRY RUN\]" dry_run_output.log || echo "Missing dry-run markers"
   grep -q "Would download" dry_run_output.log || echo "Missing download message"
   grep -q "Would extract" dry_run_output.log || echo "Missing extract message"
   ```

3. **File System Verification**
   ```bash
   # Ensure no files are created
   OUTPUT_DIR=$(mktemp -d)
   python -m dnd_notetaker FILE_ID --dry-run --output-dir $OUTPUT_DIR
   
   # Directory should remain empty
   [ -z "$(ls -A $OUTPUT_DIR)" ] && echo "✓ No files created" || echo "✗ Files were created!"
   ```

### Edge Cases and Error Scenarios

1. **Invalid File ID**
   ```bash
   python -m dnd_notetaker INVALID_ID --dry-run
   # Should still show what would happen, not fail
   ```

2. **Missing Dependencies**
   ```bash
   # Test without ffmpeg installed
   sudo apt remove ffmpeg -y
   python -m dnd_notetaker FILE_ID --dry-run
   # Should complete successfully (no actual ffmpeg call)
   ```

3. **Combined with Other Flags**
   ```bash
   # Test with various flag combinations
   python -m dnd_notetaker FILE_ID --dry-run --output-dir /custom/path
   python -m dnd_notetaker FILE_ID --dry-run --config custom.json
   python -m dnd_notetaker --dry-run  # No file ID
   ```

4. **Permission Issues**
   ```bash
   # Test with read-only output directory
   mkdir -p /tmp/readonly && chmod 444 /tmp/readonly
   python -m dnd_notetaker FILE_ID --dry-run --output-dir /tmp/readonly
   # Should complete (no actual write attempts)
   ```

### Manual Testing

```bash
# Basic dry run
python -m dnd_notetaker FILE_ID --dry-run

# Dry run with custom output directory
python -m dnd_notetaker FILE_ID --dry-run --output-dir /tmp/test

# Dry run with config file
python -m dnd_notetaker FILE_ID --dry-run --config my-config.json
```

### Automated Testing in Makefile

The `make test` command should include a dry-run test to ensure the feature works correctly:

```makefile
test: ## Run test suite
	@echo "$(GREEN)Running type checks...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pyright; \
	else \
		python -m pyright; \
	fi
	@echo "$(GREEN)Running tests...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pytest; \
	else \
		python -m pytest; \
	fi
	@echo "$(GREEN)Testing dry-run mode...$(NC)"
	@if [ -d "venv" ]; then \
		./venv/bin/python -m dnd_notetaker --dry-run || echo "$(YELLOW)Note: --dry-run flag not yet implemented$(NC)"; \
	else \
		python -m dnd_notetaker --dry-run || echo "$(YELLOW)Note: --dry-run flag not yet implemented$(NC)"; \
	fi
```

This will:
- Run pyright type checking first
- Run the pytest suite
- Test the --dry-run flag (gracefully handling if not yet implemented)

### Testing Checklist

Before considering the dry-run feature complete, verify each item:

#### Core Functionality
- [ ] `--dry-run` flag is recognized by CLI parser
- [ ] Flag value is passed to Config class
- [ ] Config.dry_run property is accessible by all components
- [ ] All components check dry_run before expensive operations

#### No Side Effects
- [ ] No files are downloaded from Google Drive
- [ ] No audio files are extracted
- [ ] No API calls to OpenAI (Whisper or GPT)
- [ ] No output files are created
- [ ] No directories are created
- [ ] No network connections are made

#### Output Verification
- [ ] Each major operation prints a "[DRY RUN]" prefixed message
- [ ] Messages clearly indicate what would happen
- [ ] File paths are shown for transparency
- [ ] Estimated costs/sizes are shown where applicable
- [ ] Output is formatted consistently

#### Component Testing
- [ ] SimplifiedDriveHandler returns dummy paths without downloading
- [ ] AudioExtractor returns dummy paths without running FFmpeg
- [ ] Transcriber returns dummy transcript without API calls
- [ ] NoteGenerator returns dummy notes without API calls
- [ ] Artifacts are NOT saved to disk

#### Error Handling
- [ ] Missing credentials don't cause failures
- [ ] Invalid file IDs are handled gracefully
- [ ] Permission errors don't occur (no actual file operations)
- [ ] Network errors don't occur (no actual network calls)

#### Integration
- [ ] Works with --output-dir flag
- [ ] Works with --config flag
- [ ] Works without any file ID (shows help or appropriate message)
- [ ] Exit code is 0 (success) after dry-run

### Verification Matrix

| Component | Dry-Run Check | Mock Return | Log Output | Test Coverage |
|-----------|---------------|-------------|------------|---------------|
| Config | N/A | N/A | N/A | ✓ Unit test |
| CLI Parser | N/A | N/A | N/A | ✓ Unit test |
| SimplifiedDriveHandler | ✓ Before download | Output path | "[DRY RUN] Would download..." | ✓ Unit + Integration |
| AudioExtractor | ✓ Before FFmpeg | Audio path | "[DRY RUN] Would extract..." | ✓ Unit + Integration |
| Transcriber | ✓ Before API call | {"text": "..."} | "[DRY RUN] Would transcribe..." | ✓ Unit + Integration |
| NoteGenerator | ✓ Before API call | "Notes string" | "[DRY RUN] Would generate..." | ✓ Unit + Integration |
| Artifacts | ✓ Before save | None | "[DRY RUN] Would save..." | ✓ Unit + Integration |

### Performance Verification

Dry-run mode should be significantly faster than normal operation:

```bash
# Time normal operation
time python -m dnd_notetaker FILE_ID

# Time dry-run operation
time python -m dnd_notetaker FILE_ID --dry-run

# Dry-run should complete in < 1 second
```

## Migration Plan

### Phase 1: Core Implementation

1. Add `--dry-run` flag to `meet_notes.py`
2. Update `Config` class to accept and store dry_run parameter
3. Pass dry_run flag from CLI to Config

### Phase 2: Component Updates

1. Update `MeetProcessor` to pass config to all components
2. Add dry_run checks to `SimplifiedDriveHandler`
3. Add dry_run checks to `AudioExtractor`
4. Add dry_run checks to `Transcriber`
5. Add dry_run checks to `NoteGenerator`

### Phase 3: Documentation

1. Update README with --dry-run usage examples
2. Add dry-run to command help text
3. Document expected output format

### Files to Update

- `src/dnd_notetaker/meet_notes.py` - Add CLI flag and pass to Config
- `src/dnd_notetaker/config.py` - Add dry_run parameter
- `src/dnd_notetaker/meet_processor.py` - Pass config to components
- `src/dnd_notetaker/simplified_drive_handler.py` - Add dry_run checks
- `src/dnd_notetaker/audio_extractor.py` - Add dry_run checks
- `src/dnd_notetaker/transcriber.py` - Add dry_run checks
- `src/dnd_notetaker/note_generator.py` - Add dry_run checks
- `README.md` - Document --dry-run usage
- `Makefile` - Add dry-run test to the test command

## Success Criteria

1. Can run full pipeline with --dry-run without any external calls
2. Clear, informative output showing what would happen
3. No files created or modified in dry-run mode
4. Pipeline completes successfully with dummy values
5. Easy to understand what operations would be performed

## Example Output

```bash
$ python -m dnd_notetaker ABC123 --dry-run
[DRY RUN] Would download Google Drive file:
  File ID: ABC123
  Output path: /tmp/dnd_output/video.mp4
  
[DRY RUN] Would extract audio using FFmpeg:
  Input: /tmp/dnd_output/video.mp4
  Output: /tmp/dnd_output/audio.mp3
  Command: ffmpeg -i /tmp/dnd_output/video.mp4 -vn -acodec libmp3lame /tmp/dnd_output/audio.mp3
  
[DRY RUN] Would transcribe audio using OpenAI Whisper:
  Audio file: /tmp/dnd_output/audio.mp3
  Model: gpt-4o-transcribe
  Estimated cost: ~$0.006 per minute
  
[DRY RUN] Would generate notes using OpenAI GPT:
  Model: gpt-4-turbo-preview
  Transcript length: 0 characters
  Estimated tokens: ~0
  
[DRY RUN] Would save artifacts to: /tmp/dnd_output/
  - notes.md
  - transcript.json
  - audio.mp3
```