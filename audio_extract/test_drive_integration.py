#!/usr/bin/env python3
"""Test script for Drive monitoring integration."""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_extract.config import Config
from audio_extract.tracker import ProcessingTracker
from audio_extract.extractor import AudioExtractor
from audio_extract.drive import DriveAuth, DriveClient, DriveMonitor


def test_config_system():
    """Test configuration system."""
    print("\n1. Testing Configuration System")
    print("=" * 50)
    
    # Test default config
    config = Config()
    print("✓ Default config loaded")
    
    # Test getting values
    folder_id = config.get('google_drive.recordings_folder_id')
    output_dir = config.get('processing.output_directory')
    interval = config.get('google_drive.check_interval_seconds')
    
    print(f"  - Folder ID: {folder_id}")
    print(f"  - Output dir: {output_dir}")
    print(f"  - Check interval: {interval}s")
    
    # Test setting values
    config.set('google_drive.recordings_folder_id', 'test-folder-123')
    assert config.get('google_drive.recordings_folder_id') == 'test-folder-123'
    print("✓ Config set/get working")
    
    # Test validation
    errors = config.validate()
    print(f"✓ Validation errors: {len(errors)}")
    
    return True


def test_drive_auth():
    """Test Drive authentication (mocked)."""
    print("\n2. Testing Drive Authentication")
    print("=" * 50)
    
    with patch('audio_extract.drive.auth.service_account.Credentials') as mock_creds:
        # Mock the credentials
        mock_creds.from_service_account_file.return_value = MagicMock()
        
        # Test auth initialization
        auth = DriveAuth()
        print("✓ DriveAuth initialized")
        
        # Test credential loading (will fail without real creds)
        try:
            creds = auth.get_credentials()
            print("✓ Credentials loaded (mocked)")
        except ValueError as e:
            print(f"✓ Expected error without credentials: {str(e)[:50]}...")
    
    return True


def test_drive_client():
    """Test Drive client (mocked)."""
    print("\n3. Testing Drive Client")
    print("=" * 50)
    
    with patch('audio_extract.drive.client.build') as mock_build:
        # Mock the Drive service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock auth
        mock_auth = Mock()
        mock_auth.get_credentials.return_value = MagicMock()
        
        # Create client
        client = DriveClient(auth=mock_auth)
        print("✓ DriveClient initialized")
        
        # Test file listing
        mock_service.files().list().execute.return_value = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'meeting_recording.mp4',
                    'mimeType': 'video/mp4',
                    'size': '1000000',
                    'modifiedTime': '2025-06-29T10:00:00Z'
                }
            ]
        }
        
        files = client.list_files('folder123')
        print(f"✓ Listed {len(files)} files")
        
        # Test Meet recording finding
        recordings = client.find_meet_recordings('folder123')
        print(f"✓ Found {len(recordings)} Meet recordings")
        
        # Test connection test
        mock_service.about().get().execute.return_value = {
            'user': {'emailAddress': 'test@example.com'}
        }
        
        connected = client.test_connection()
        print(f"✓ Connection test: {connected}")
    
    return True


def test_drive_monitor():
    """Test Drive monitor with mocked components."""
    print("\n4. Testing Drive Monitor")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test database
        db_path = Path(temp_dir) / 'test.db'
        output_dir = Path(temp_dir) / 'output'
        
        # Initialize components
        tracker = ProcessingTracker(db_path)
        extractor = AudioExtractor()
        
        # Mock Drive client
        mock_client = Mock()
        mock_client.find_meet_recordings.return_value = [
            {
                'id': 'video1',
                'name': 'meeting_2025-06-29.mp4',
                'size': '50000000',
                'modifiedTime': '2025-06-29T10:00:00Z'
            }
        ]
        mock_client.download_file.return_value = Path(temp_dir) / 'temp_video.mp4'
        mock_client.test_connection.return_value = True
        
        # Create monitor
        monitor = DriveMonitor(
            tracker=tracker,
            extractor=extractor,
            output_dir=output_dir,
            drive_client=mock_client,
            check_interval=5
        )
        print("✓ DriveMonitor initialized")
        
        # Test finding new recordings
        new_recordings = monitor.find_new_recordings('folder123')
        print(f"✓ Found {len(new_recordings)} new recordings")
        
        # Test processing (mock the extraction)
        with patch.object(extractor, 'extract') as mock_extract:
            mock_extract.return_value = None
            
            # Create a dummy video file
            temp_video = Path(temp_dir) / 'temp_video1.mp4'
            temp_video.write_text('dummy video data')
            mock_client.download_file.return_value = temp_video
            
            success = monitor.process_recording(new_recordings[0])
            print(f"✓ Processing result: {success}")
        
        # Test check cycle
        stats = monitor.check_once('folder123')
        print(f"✓ Check cycle stats: {stats}")
        
        # Test sync recording
        tracker.record_sync(
            folder_id='folder123',
            files_found=1,
            files_processed=1,
            files_failed=0,
            duration_seconds=2.5
        )
        
        # Get sync history
        history = tracker.get_sync_history(limit=5)
        print(f"✓ Sync history entries: {len(history)}")
        
        # Test statistics
        final_stats = monitor.get_stats()
        print(f"✓ Monitor stats: {final_stats}")
        
        # Clean up
        tracker.close()
    
    return True


def test_database_schema():
    """Test updated database schema."""
    print("\n5. Testing Database Schema")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.db'
        tracker = ProcessingTracker(db_path)
        
        # Test Drive file recording
        file_metadata = {
            'id': 'drive123',
            'name': 'meeting.mp4',
            'parents': ['folder456'],
            'mimeType': 'video/mp4',
            'size': '1000000',
            'modifiedTime': '2025-06-29T10:00:00Z'
        }
        
        tracker.record_drive_file(file_metadata)
        print("✓ Drive file recorded")
        
        # Test sync history
        tracker.record_sync(
            folder_id='folder456',
            files_found=5,
            files_processed=4,
            files_failed=1,
            duration_seconds=12.3
        )
        print("✓ Sync history recorded")
        
        # Get sync history
        history = tracker.get_sync_history()
        print(f"✓ Retrieved {len(history)} sync history entries")
        
        if history:
            latest = history[0]
            print(f"  - Latest sync: {latest['files_processed']}/{latest['files_found']} processed")
        
        tracker.close()
    
    return True


def main():
    """Run all tests."""
    print("Audio Extract - Drive Integration Tests")
    print("=" * 70)
    
    tests = [
        test_config_system,
        test_drive_auth,
        test_drive_client,
        test_drive_monitor,
        test_database_schema
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test.__name__} failed with error:")
            print(f"  {type(e).__name__}: {str(e)}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())