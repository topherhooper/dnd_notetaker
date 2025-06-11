import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnd_notetaker.drive_handler import DriveHandler


class TestDriveHandler:
    """Test drive handler functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("dnd_notetaker.drive_handler.GoogleAuthenticator")
    def test_download_file_creates_directory(self, mock_auth):
        """Test that download_file creates the directory if it doesn't exist"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())

        # Create handler
        handler = DriveHandler()

        # Mock the Drive API response with all required fields
        mock_file = Mock()
        mock_file.execute.return_value = {
            "name": "test_video.mp4",
            "mimeType": "video/mp4",
            "size": "1024000",
        }
        mock_drive_service.files.return_value.get.return_value = mock_file

        # Mock the download
        mock_request = Mock()
        mock_downloader = Mock()
        mock_downloader.next_chunk.side_effect = [
            (Mock(progress=Mock(return_value=0.5)), False),
            (Mock(progress=Mock(return_value=1.0)), True),
        ]

        with patch(
            "dnd_notetaker.drive_handler.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            with patch("builtins.open", create=True):
                # Mock os.path.getsize for the final size check
                with patch("os.path.getsize", return_value=1024000):
                    # Use a non-existent directory
                    download_dir = os.path.join(self.test_dir, "non_existent_dir")

                    # This should create the directory and not raise an error
                    result = handler.download_file("fake_file_id", download_dir)

                    # Verify directory was created
                    assert os.path.exists(download_dir)
                    assert result == os.path.join(download_dir, "test_video.mp4")

    @patch("dnd_notetaker.drive_handler.GoogleAuthenticator")
    def test_download_file_handles_complex_filename(self, mock_auth):
        """Test that download handles complex filenames with special characters"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())

        # Create handler
        handler = DriveHandler()

        # Test with a complex filename
        complex_filename = "DnD - 2025-06-06 18-49 CDT - Recording.mp4"

        # Mock the Drive API response with all required fields
        mock_file = Mock()
        mock_file.execute.return_value = {
            "name": complex_filename,
            "mimeType": "video/mp4",
            "size": "1024000",
        }
        mock_drive_service.files.return_value.get.return_value = mock_file

        # Mock the download
        mock_request = Mock()
        mock_downloader = Mock()
        mock_downloader.next_chunk.side_effect = [
            (Mock(progress=Mock(return_value=1.0)), True)
        ]

        with patch(
            "dnd_notetaker.drive_handler.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            # Create a mock file content
            with patch("builtins.open", create=True) as mock_open:
                mock_file_handle = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file_handle

                # Mock os.path.getsize for the final size check
                with patch("os.path.getsize", return_value=1024000):
                    download_dir = os.path.join(self.test_dir, "downloads")
                    os.makedirs(download_dir, exist_ok=True)

                    result = handler.download_file("fake_file_id", download_dir)

                    # Verify the file path is constructed correctly
                    expected_path = os.path.join(
                        download_dir, "DnD - 2025-06-06 18-49 CDT - Recording.mp4"
                    )
                    assert result == expected_path

                    # Verify open was called with the correct path
                    mock_open.assert_called_once_with(expected_path, "wb")

    @patch("dnd_notetaker.drive_handler.GoogleAuthenticator")
    def test_sanitize_filename(self, mock_auth):
        """Test filename sanitization"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())
        
        handler = DriveHandler()

        # Test various problematic filenames
        test_cases = [
            ("normal_file.mp4", "normal_file.mp4"),
            ("file/with/slashes.mp4", "file-with-slashes.mp4"),
            ("file:with:colons.mp4", "file-with-colons.mp4"),
            ("file\\with\\backslashes.mp4", "file-with-backslashes.mp4"),
            ("file<>with|special*chars?.mp4", "file--with-special-chars-.mp4"),
        ]

        for input_name, expected in test_cases:
            assert handler.sanitize_filename(input_name) == expected

    @patch("dnd_notetaker.drive_handler.GoogleAuthenticator")
    def test_list_recordings(self, mock_auth):
        """Test listing recordings from Drive folder"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())
        
        handler = DriveHandler()
        
        # Mock the Drive API response
        mock_files_list = {
            "files": [
                {
                    "id": "file1",
                    "name": "DnD - 2025-01-10 Recording.mp4",
                    "size": "104857600",  # 100 MB
                    "mimeType": "video/mp4",
                    "createdTime": "2025-01-10T18:00:00Z",
                    "modifiedTime": "2025-01-10T19:00:00Z"
                },
                {
                    "id": "file2",
                    "name": "DnD - 2025-01-03 Recording.mp4",
                    "size": "209715200",  # 200 MB
                    "mimeType": "video/mp4",
                    "createdTime": "2025-01-03T18:00:00Z",
                    "modifiedTime": "2025-01-03T19:00:00Z"
                }
            ]
        }
        
        mock_drive_service.files.return_value.list.return_value.execute.return_value = mock_files_list
        
        # Test the method
        recordings = handler.list_recordings()
        
        # Verify the results
        assert len(recordings) == 2
        assert recordings[0]["index"] == 1
        assert recordings[0]["file_name"] == "DnD - 2025-01-10 Recording.mp4"
        assert recordings[0]["file_size_mb"] == 100.0
        assert recordings[0]["file_id"] == "file1"
        assert recordings[1]["index"] == 2
        assert recordings[1]["file_name"] == "DnD - 2025-01-03 Recording.mp4"
        assert recordings[1]["file_size_mb"] == 200.0
        assert recordings[1]["file_id"] == "file2"
        
        # Verify the API was called with correct parameters
        mock_drive_service.files.return_value.list.assert_called_once()
        call_args = mock_drive_service.files.return_value.list.call_args
        assert "14EVI64FlpZCwRy4UL4ZhGjlsjK55XL1h" in call_args[1]["q"]

    @patch("dnd_notetaker.drive_handler.GoogleAuthenticator")
    def test_find_recording_by_name(self, mock_auth):
        """Test finding a recording by name filter"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())
        
        handler = DriveHandler()
        
        # Mock the list_recordings response
        mock_recordings = [
            {
                "index": 1,
                "file_name": "DnD - 2025-01-10 Recording.mp4",
                "file_id": "file1",
                "file_size_mb": 100.0
            },
            {
                "index": 2,
                "file_name": "DnD - 2025-01-03 Recording.mp4",
                "file_id": "file2",
                "file_size_mb": 200.0
            }
        ]
        
        with patch.object(handler, 'list_recordings', return_value=mock_recordings):
            # Test finding by partial name
            result = handler.find_recording_by_name("2025-01-10")
            assert result is not None
            assert result["file_id"] == "file1"
            
            # Test case insensitive
            result = handler.find_recording_by_name("dnd")
            assert result is not None
            
            # Test no match
            result = handler.find_recording_by_name("nonexistent")
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])