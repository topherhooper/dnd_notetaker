import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnd_notetaker.email_handler import EmailHandler


class TestEmailHandlerDownload:
    """Test download functionality of EmailHandler"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.credentials = {
            "email": "test@example.com",
            "password": "testpass",
            "imap_server": "imap.gmail.com",
        }

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("dnd_notetaker.email_handler.GoogleAuthenticator")
    def test_download_from_drive_creates_directory(self, mock_auth):
        """Test that download_from_drive creates the directory if it doesn't exist"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())

        # Create handler
        handler = EmailHandler(self.credentials)

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
            "dnd_notetaker.email_handler.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            with patch("builtins.open", create=True):
                # Mock os.path.getsize for the final size check
                with patch("os.path.getsize", return_value=1024000):
                    # Use a non-existent directory
                    download_dir = os.path.join(self.test_dir, "non_existent_dir")

                    # This should create the directory and not raise an error
                    result = handler.download_from_drive("fake_file_id", download_dir)

                    # Verify directory was created
                    assert os.path.exists(download_dir)
                    assert result == os.path.join(download_dir, "test_video.mp4")

    @patch("dnd_notetaker.email_handler.GoogleAuthenticator")
    def test_download_from_drive_handles_complex_filename(self, mock_auth):
        """Test that download handles complex filenames with special characters"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())

        # Create handler
        handler = EmailHandler(self.credentials)

        # Test with a complex filename like the one in the error
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
            "dnd_notetaker.email_handler.MediaIoBaseDownload",
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

                    result = handler.download_from_drive("fake_file_id", download_dir)

                    # Verify the file path is constructed correctly (sanitize_filename keeps the extension)
                    expected_path = os.path.join(
                        download_dir, "DnD - 2025-06-06 18-49 CDT - Recording.mp4"
                    )
                    assert result == expected_path

                    # Verify open was called with the correct path
                    mock_open.assert_called_once_with(expected_path, "wb")

    @patch("dnd_notetaker.email_handler.GoogleAuthenticator")
    def test_sanitize_filename(self, mock_auth):
        """Test filename sanitization"""
        # Mock the authentication
        mock_drive_service = Mock()
        mock_auth.return_value.get_services.return_value = (mock_drive_service, Mock())
        
        handler = EmailHandler(self.credentials)

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
