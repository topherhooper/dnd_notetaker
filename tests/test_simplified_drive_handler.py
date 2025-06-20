"""Tests for the simplified Google Drive handler"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import io

from dnd_notetaker.simplified_drive_handler import SimplifiedDriveHandler


class TestSimplifiedDriveHandler:
    """Test Google Drive download functionality"""
    
    @pytest.fixture
    def mock_service_account_file(self, tmp_path):
        """Create a mock service account file"""
        sa_file = tmp_path / "service_account.json"
        sa_file.write_text('{"type": "service_account"}')
        return sa_file
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_init(self, mock_sa, mock_build, mock_service_account_file):
        """Test drive handler initialization"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Create handler
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        # Verify credentials were loaded
        mock_sa.Credentials.from_service_account_file.assert_called_once_with(
            str(mock_service_account_file),
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Verify service was built
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_creds)
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_download_file_success(self, mock_sa, mock_build, mock_service_account_file, tmp_path):
        """Test successful file download"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Setup mocks
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock file metadata
        file_metadata = {
            'name': 'meeting_recording.mp4',
            'size': '104857600',  # 100MB
            'mimeType': 'video/mp4'
        }
        mock_service.files().get().execute.return_value = file_metadata
        
        # Mock file download
        mock_request = Mock()
        mock_service.files().get_media.return_value = mock_request
        
        # Mock downloader
        file_content = b"fake video content"
        mock_fh = io.BytesIO(file_content)
        
        with patch('io.BytesIO', return_value=mock_fh):
            with patch('googleapiclient.http.MediaIoBaseDownload') as mock_downloader_class:
                mock_downloader = Mock()
                mock_downloader.next_chunk.side_effect = [
                    (Mock(progress=lambda: 0.5), False),
                    (Mock(progress=lambda: 1.0), True)
                ]
                mock_downloader_class.return_value = mock_downloader
                
                # Create handler and download
                handler = SimplifiedDriveHandler(mock_service_account_file)
                output_dir = tmp_path / "output"
                output_dir.mkdir()
                
                result = handler.download_file("file123", output_dir)
                
                # Verify file was created
                expected_path = output_dir / "meeting_recording.mp4"
                assert result == expected_path
                assert expected_path.exists()
                assert expected_path.read_bytes() == file_content
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_download_file_not_video(self, mock_sa, mock_build, mock_service_account_file, tmp_path):
        """Test error when file is not a video"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Setup mocks
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock non-video file metadata
        file_metadata = {
            'name': 'document.pdf',
            'size': '1024',
            'mimeType': 'application/pdf'
        }
        mock_service.files().get().execute.return_value = file_metadata
        
        # Create handler and try to download
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        with pytest.raises(ValueError, match="File is not a video"):
            handler.download_file("file123", tmp_path)
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_download_most_recent_success(self, mock_sa, mock_build, mock_service_account_file, tmp_path):
        """Test downloading the most recent recording"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Setup mocks
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock file list
        files_list = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'Meet Recording 1.mp4',
                    'modifiedTime': '2024-01-19T10:00:00Z',
                    'mimeType': 'video/mp4'
                },
                {
                    'id': 'file2',
                    'name': 'Document.pdf',
                    'modifiedTime': '2024-01-19T11:00:00Z',
                    'mimeType': 'application/pdf'
                },
                {
                    'id': 'file3',
                    'name': 'Meet Recording 2.mp4',
                    'modifiedTime': '2024-01-19T09:00:00Z',
                    'mimeType': 'video/mp4'
                }
            ]
        }
        mock_service.files().list().execute.return_value = files_list
        
        # Create handler
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        # Mock the download_file method
        with patch.object(handler, 'download_file') as mock_download:
            mock_download.return_value = tmp_path / "meeting.mp4"
            
            # Download most recent
            result = handler.download_most_recent(tmp_path)
            
            # Verify it downloaded the first video file (most recent)
            mock_download.assert_called_once_with('file1', tmp_path)
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_download_most_recent_no_videos(self, mock_sa, mock_build, mock_service_account_file, tmp_path):
        """Test error when no recordings are found"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Setup mocks
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock empty file list
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Create handler and try to download
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        with pytest.raises(ValueError, match="No Meet recordings found"):
            handler.download_most_recent(tmp_path)
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_download_most_recent_fallback(self, mock_sa, mock_build, mock_service_account_file, tmp_path):
        """Test fallback when no video mime type but Meet in name"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        # Setup mocks
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock file list with no video mime types
        files_list = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'Meet Recording.mp4',
                    'modifiedTime': '2024-01-19T10:00:00Z',
                    'mimeType': 'application/octet-stream'  # Generic mime type
                }
            ]
        }
        mock_service.files().list().execute.return_value = files_list
        
        # Create handler
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        # Mock the download_file method
        with patch.object(handler, 'download_file') as mock_download:
            mock_download.return_value = tmp_path / "meeting.mp4"
            
            # Download most recent
            result = handler.download_most_recent(tmp_path)
            
            # Verify it downloaded the file (fallback)
            mock_download.assert_called_once_with('file1', tmp_path)
    
    @patch('dnd_notetaker.simplified_drive_handler.build')
    @patch('dnd_notetaker.simplified_drive_handler.service_account')
    def test_format_size(self, mock_sa, mock_build, mock_service_account_file):
        """Test file size formatting"""
        # Mock credentials
        mock_creds = Mock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        
        handler = SimplifiedDriveHandler(mock_service_account_file)
        
        test_cases = [
            (500, "500.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (1099511627776, "1.0 TB")
        ]
        
        for size, expected in test_cases:
            assert handler._format_size(size) == expected
    
    def test_dry_run_init(self, mock_service_account_file):
        """Test drive handler initialization in dry run mode"""
        config = Mock(dry_run=True)
        
        # No patching needed - should not create service in dry run
        handler = SimplifiedDriveHandler(mock_service_account_file, config)
        
        # Service should be None in dry run
        assert handler.service is None
        assert handler.config == config
    
    @patch('builtins.print')
    def test_download_file_dry_run(self, mock_print, mock_service_account_file, tmp_path):
        """Test download_file in dry run mode"""
        config = Mock(dry_run=True)
        handler = SimplifiedDriveHandler(mock_service_account_file, config)
        
        output_dir = tmp_path / "output"
        result = handler.download_file("file123", output_dir)
        
        # Should return expected path without downloading
        assert result == output_dir / "meeting.mp4"
        
        # Should print dry run messages
        mock_print.assert_any_call("[DRY RUN] Would download from Google Drive:")
        mock_print.assert_any_call("  File ID: file123")
        mock_print.assert_any_call(f"  Destination: {output_dir / 'meeting.mp4'}")
        
        # Should not create any files
        assert not (output_dir / "meeting.mp4").exists()
    
    @patch('builtins.print')
    def test_download_most_recent_dry_run(self, mock_print, mock_service_account_file, tmp_path):
        """Test download_most_recent in dry run mode"""
        config = Mock(dry_run=True)
        handler = SimplifiedDriveHandler(mock_service_account_file, config)
        
        result = handler.download_most_recent(tmp_path)
        
        # Should return expected path without downloading
        assert result == tmp_path / "meeting.mp4"
        
        # Should print dry run messages
        mock_print.assert_any_call("[DRY RUN] Would search for most recent Google Meet recording")
        mock_print.assert_any_call(f"[DRY RUN] Would download most recent file to: {tmp_path / 'meeting.mp4'}")