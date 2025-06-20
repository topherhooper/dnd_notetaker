# Simplification Plan: Core Features for Google Meet Processing

## Overview

Transform the D&D Notetaker from a complex multi-mode tool into a streamlined, single-purpose application focused on processing Google Meet recordings with excellent reliability and user experience.

## Motivation

The current codebase has accumulated significant complexity:
- 8 different ways to run the same pipeline
- Complex directory management and checkpointing
- Multiple CLI interfaces for individual components
- Extensive configuration and setup requirements
- Features that distract from the core value proposition

This complexity makes the tool harder to maintain, test, and use effectively.

## Core Value Proposition

Given a Google Meet recording, produce:
1. **Audio file** - Extracted from the video
2. **Transcription** - Accurate text from the audio
3. **Generated notes** - Prose-style narrative summary (no formatting, bullets, or structure)
4. **Easy sharing** - All artifacts accessible via shareable links

## Technical Approach

### 1. Simplified Architecture

```
Google Drive → Audio Extraction → Transcription → Note Generation → Sharing
```

**Key Classes (Simplified)**:
- `MeetProcessor` - Main orchestrator (renamed from MeetingProcessor)
- `AudioExtractor` - Extract audio from video (simplified AudioProcessor)
- `Transcriber` - Convert audio to text (keep as-is)
- `NoteGenerator` - Create structured notes (simplified TranscriptProcessor)
- `Artifacts` - Manage and share all outputs (new)

### 2. Single Entry Point

```python
# Default: Process most recent recording
python -m meet_notes

# Specific recording by ID
python -m meet_notes FILE_ID

# That's it!
```

### 3. Simplified Output Structure

```
meet_notes_output/
└── 2025_01_19_150230/  # Simple timestamp
    ├── meeting.mp4      # Original video
    ├── audio.mp3        # Extracted audio
    ├── transcript.txt   # Raw transcription
    ├── notes.txt        # Generated prose notes (plain text)
    └── artifacts.json   # Metadata and share links
```

### 4. Unified Sharing Solution

Instead of just Google Docs, create a simple sharing mechanism:
- Generate a unique share ID
- Create a simple HTML page with all artifacts
- Upload to a cloud storage with public link
- Single URL gives access to everything

### 5. Configuration Simplification

Single config file at `.credentials/config.json`:
```json
{
  "openai_api_key": "sk-...",
  "google_service_account": "path/to/service_account.json",
  "output_dir": "~/meet_notes_output"
}
```

### 6. Features to Remove

1. **All alternative CLIs** - No Makefile, no individual component CLIs
2. **Interactive mode** - Too complex for minimal value
3. **Temporary file management** - Just use timestamped output dirs
4. **Complex resume logic** - Simplify to basic file existence checks
5. **Directory naming logic** - Simple timestamps are sufficient
6. **Age-based cleanup** - Users can manage their own files
7. **Multiple output options** - One standard output structure
8. **Public sharing toggle** - Always create shareable artifacts

### 7. Features to Enhance

1. **Progress reporting** - Clear, simple progress bar
2. **Error messages** - User-friendly, actionable errors
3. **Performance** - Optimize for large recordings (parallel processing)
4. **Reliability** - Better retry logic for API calls
5. **Note generation quality** - Focus on natural prose output

### 8. Note Generation Approach

The generated notes should read like a well-written narrative summary:
- **No bullet points or lists** - Pure flowing prose
- **No headers or sections** - Continuous narrative
- **Natural language** - As if someone is telling you what happened
- **Chronological flow** - Follow the meeting's progression naturally
- **Key details preserved** - Important decisions, action items woven into the narrative

Example output style:
```
The meeting began with John discussing the upcoming product launch scheduled for March. Sarah raised concerns about the timeline, particularly around the testing phase which she felt needed at least two more weeks. After some discussion, the team agreed to push the launch to early April to ensure quality. Michael committed to updating the project timeline and communicating the change to stakeholders by end of week...
```

### 9. Simple Checkpointing Strategy

To avoid losing progress on large recordings, implement minimal checkpointing:

```python
# Check if step already completed
if os.path.exists(output_dir / "audio.mp3"):
    print("✓ Audio already extracted, skipping...")
else:
    extract_audio(video_path, output_dir / "audio.mp3")

if os.path.exists(output_dir / "transcript.txt"):
    print("✓ Transcript exists, skipping...")
else:
    transcribe_audio(output_dir / "audio.mp3", output_dir / "transcript.txt")

# Always regenerate notes (they're fast and we might want to improve them)
generate_notes(output_dir / "transcript.txt", output_dir / "notes.txt")
```

Benefits:
- Prevents re-processing expensive operations (audio extraction, transcription)
- Simple file existence checks (no complex state management)
- Clear user feedback about what's being skipped
- Can force fresh processing by deleting output directory

## Implementation Plan

### Phase 1: Core Simplification
1. Create new simplified entry point
2. Merge essential functionality from existing classes
3. Remove all alternative interfaces
4. Implement unified output structure

### Phase 2: Enhanced Sharing
1. Design artifact bundling system
2. Implement HTML generation for viewing
3. Add cloud upload capability
4. Generate single shareable link

### Phase 3: Polish
1. Improve error handling and messages
2. Add progress indicators
3. Optimize performance for large files
4. Enhance note generation quality

## Impact Analysis

### What Users Lose
- Flexibility of multiple interfaces
- Ability to run individual components
- Complex directory organization
- Complex checkpoint management (but keep simple version)

### What Users Gain
- Dead-simple interface
- Faster processing
- Better reliability
- Single link to share everything
- Cleaner codebase that's easier to extend

## Testing Strategy

1. **End-to-end tests** - Full pipeline with sample recordings
2. **API mocking** - Test without real API calls
3. **Large file tests** - Ensure performance with 2+ hour recordings
4. **Error scenarios** - Network failures, API limits, invalid inputs

## Migration Plan

1. Create new simplified version alongside existing code ✓
2. Test with real recordings
3. Document migration path for existing users ✓
4. Deprecate old interfaces ✓
5. Remove legacy code after transition period ✓

### Files Removed

1. **Build/Setup Files**
   - `Makefile` - Complex build automation
   - `scripts/setup.sh` - Legacy setup script  
   - `scripts/cleanup.sh` - Simple cleanup script
   - `scripts/setup_credentials.py` - Legacy credential setup
   - `stratch.sh` - Scratch file

2. **Legacy Core Files**
   - `src/dnd_notetaker/main.py` - Complex CLI with all removed features
   - `src/dnd_notetaker/transcript_processor.py` - Replaced by note_generator.py

3. **Test Files**
   - `tests/test_main.py` - Tests for removed main.py
   - `tests/test_setup_credentials.py` - Tests for removed setup script
   - Removed test classes from `tests/test_utils.py`:
     - `TestCleanupOldTempDirectories`
     - `TestListTempDirectories`

4. **Removed Functions**
   - CLI main() functions from all component files
   - `cleanup_old_temp_directories()` from utils.py
   - `list_temp_directories()` from utils.py

## Success Metrics

- **Simplicity**: 80% less code
- **Reliability**: 99% success rate on valid inputs
- **Performance**: Process 2-hour recording in <10 minutes
- **Usability**: New user can process first recording in <2 minutes