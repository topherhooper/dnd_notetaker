# Add Public Sharing, Upgrade Transcript Processing, and Remove OAuth Support

## Summary

This PR adds automatic public sharing functionality to generated Google Docs, replaces the old transcript processor with an improved version featuring better speaker identification and narrative structuring, and removes OAuth authentication in favor of service account-only authentication. Documents created by the D&D notetaker will now be automatically accessible to anyone with the link (read-only), making it easier to share session notes with players.

## Key Changes

### 🔗 Document Sharing Feature

- Modified `DocsUploader.upload_notes()` to automatically share documents publicly by default
- Added `share_publicly` parameter (default `True`) to control sharing behavior
- Added `--no-public-share` CLI flag for cases where public sharing should be disabled
- Documents are shared with "anyone with link" permission in read-only mode

### 🎯 Upgraded Transcript Processing

- Replaced old transcript processor with improved version featuring:
  - Enhanced speaker identification using GPT-4
  - Better narrative structuring with scene breaks and improved dialogue formatting
  - More accurate speaker attribution and character name consistency
  - Multi-stage processing: cleaning, speaker identification, and narrative creation
  - Automatic detection and removal of garbled/non-English text
- Removed experimental multi-persona processor and original processor to simplify codebase

### 🔐 Authentication Updates

- Fixed Google Drive API permission scopes to enable sharing functionality
- Added `drive.file` scope to `auth_service_account.py` for managing document permissions
- Removed OAuth authentication support entirely - now using service account authentication exclusively
- Removed `google-auth-oauthlib` dependency from requirements.txt

### 📝 Documentation Updates

- Updated CLAUDE.md to document the public sharing feature
- Added clear documentation about required Google API scopes
- Documented that the application uses service account authentication exclusively

### 🧪 Testing

- Added comprehensive unit tests for document sharing functionality
- Fixed existing tests to work with processor type changes
- All 74 tests passing
- Code formatted with black and isort

## Breaking Changes

⚠️ **OAuth Support Removed**: If you were using OAuth authentication (token.json), you'll need to switch to service account authentication. The application no longer supports interactive login.

## Required Actions After Merge

1. **Service Account Permissions**: Ensure your service account has the necessary permissions:
   - `drive.readonly` - Read access to Drive files
   - `drive.file` - Manage files created by the app (required for sharing)
   - `documents` - Create and edit Google Docs

2. **No Re-authentication Needed**: Service accounts will automatically use the new scopes on the next run.

## Testing

To test the new features:

```bash
# Process a session - uses the upgraded processor automatically
make process

# Process without public sharing
python -m dnd_notetaker.main process --no-public-share

# Test the uploader directly
python -m dnd_notetaker.docs_uploader -i notes.txt -t "Test Doc"
```

## Benefits

- 🎲 **Easy Sharing**: DMs can now share session notes with players by simply sending the Google Doc link
- 📖 **Better Narratives**: Improved transcript processor creates more readable, story-like session notes
- 🎭 **Accurate Speaker ID**: Enhanced speaker identification correctly attributes dialogue to characters
- 🔒 **Security**: Documents are read-only for anyone with the link
- 🤖 **Automation**: No manual sharing steps required after document creation
- 🚀 **Simplified Auth**: Removing OAuth reduces complexity and makes automation easier

## Files Changed

### Core Features
- `src/dnd_notetaker/docs_uploader.py` - Added sharing functionality
- `src/dnd_notetaker/transcript_processor.py` - Replaced with improved processor (formerly v2)
- `src/dnd_notetaker/main.py` - Simplified to use single processor
- **Removed**: `transcript_processor_multipersona.py`, old `transcript_processor.py`

### Authentication & Configuration
- `src/dnd_notetaker/auth_service_account.py` - Updated API scopes
- `requirements.txt` - Removed OAuth dependency

### Tests
- `tests/test_docs_uploader.py` - Added sharing tests
- `tests/test_main.py` - Fixed processor-related tests
- `tests/test_setup_credentials.py` - Removed OAuth references

### Documentation
- `CLAUDE.md` - Updated documentation for sharing and authentication
- **Removed**: `PROCESSING_OPTIONS.md` - No longer needed with single processor

---

Fixes #[issue_number] (if applicable)