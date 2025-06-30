"""Tests for the CLI monitor command."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from audio_extract.cli.monitor import main, setup_logging, handle_cycle_stats


class TestCLIMonitor:
    """Test CLI monitor functionality."""

    def test_setup_logging(self):
        """Test logging setup."""
        # Should not raise any exceptions
        setup_logging("INFO")
        setup_logging("DEBUG")

    def test_handle_cycle_stats(self, capsys):
        """Test cycle stats handler."""
        stats = {
            "found": 5,
            "processed": 3,
            "failed": 2,
            "duration": 10.5,
        }

        handle_cycle_stats(stats)

        captured = capsys.readouterr()
        assert "Cycle complete:" in captured.out
        assert "found=5" in captured.out
        assert "processed=3" in captured.out
        assert "failed=2" in captured.out
        assert "duration=10.5s" in captured.out

    @patch("audio_extract.cli.monitor.Config")
    @patch("audio_extract.cli.monitor.DriveAuth")
    @patch("audio_extract.cli.monitor.DriveClient")
    def test_test_connection_mode(self, mock_client_class, mock_auth_class, mock_config_class):
        """Test --test mode."""
        # Mock config
        mock_config = Mock()
        mock_config.validate.return_value = []
        mock_config.get.side_effect = lambda key: {
            "google_drive.recordings_folder_id": "test-folder",
            "processing.output_directory": "./test-output",
            "monitoring.database_path": "./test.db",
            "google_drive.service_account_file": None,
        }.get(key)
        mock_config_class.return_value = mock_config

        # Mock auth and client
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth

        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.list_files.return_value = [
            {"name": "file1.mp4"},
            {"name": "file2.mp4"},
        ]
        mock_client_class.return_value = mock_client

        # Test with --test flag
        test_args = ["monitor.py", "--test", "--no-health-check"]
        with patch.object(sys, "argv", test_args):
            result = main()

        assert result == 0
        mock_client.test_connection.assert_called_once()
        mock_client.list_files.assert_called_once()

    @patch("audio_extract.cli.monitor.Config")
    @patch("audio_extract.cli.monitor.DriveAuth")
    @patch("audio_extract.cli.monitor.DriveClient")
    @patch("audio_extract.cli.monitor.ProcessingTracker")
    @patch("audio_extract.cli.monitor.AudioExtractor")
    @patch("audio_extract.cli.monitor.StorageFactory")
    @patch("audio_extract.cli.monitor.StorageAwareDriveMonitor")
    def test_once_mode(
        self,
        mock_monitor_class,
        mock_storage_factory,
        mock_extractor_class,
        mock_tracker_class,
        mock_client_class,
        mock_auth_class,
        mock_config_class,
    ):
        """Test --once mode."""
        # Mock config
        mock_config = Mock()
        mock_config.validate.return_value = []
        mock_config.get.side_effect = lambda key, default=None: {
            "google_drive.recordings_folder_id": "test-folder",
            "processing.output_directory": "./test-output",
            "monitoring.database_path": "./test.db",
            "google_drive.service_account_file": None,
            "processing.audio_format.bitrate": "128k",
            "processing.audio_format.sample_rate": 44100,
            "processing.audio_format.channels": 1,
            "storage": {"type": "local", "local": {"path": "./test-output"}},
            "processing.delete_local_after_upload": False,
        }.get(key, default)
        mock_config_class.return_value = mock_config

        # Mock components
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker

        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        mock_storage = Mock()
        mock_storage_factory.create.return_value = mock_storage

        mock_monitor = Mock()
        mock_monitor.check_once.return_value = {
            "found": 2,
            "processed": 2,
            "failed": 0,
            "duration": 5.0,
        }
        mock_monitor.get_stats.return_value = {
            "total_found": 2,
            "total_processed": 2,
            "total_failed": 0,
        }
        mock_monitor_class.return_value = mock_monitor

        # Test with --once flag
        test_args = ["monitor.py", "--once", "--no-health-check"]
        with patch.object(sys, "argv", test_args):
            result = main()

        assert result == 0
        mock_monitor.check_once.assert_called_once_with("test-folder", 7)
        mock_monitor.get_stats.assert_called_once()

    @patch("audio_extract.cli.monitor.Config")
    def test_config_validation_error(self, mock_config_class):
        """Test handling of config validation errors."""
        # Mock config with validation errors
        mock_config = Mock()
        mock_config.validate.return_value = ["Missing folder ID", "Invalid output directory"]
        mock_config_class.return_value = mock_config

        # Test
        test_args = ["monitor.py", "--no-health-check"]
        with patch.object(sys, "argv", test_args):
            result = main()

        assert result == 1

    @patch("audio_extract.cli.monitor.Config")
    @patch("audio_extract.cli.monitor.DriveAuth")
    @patch("audio_extract.cli.monitor.DriveClient")
    def test_connection_failure(self, mock_client_class, mock_auth_class, mock_config_class):
        """Test handling of connection failure."""
        # Mock config
        mock_config = Mock()
        mock_config.validate.return_value = []
        mock_config.get.side_effect = lambda key: {
            "google_drive.recordings_folder_id": "test-folder",
            "processing.output_directory": "./test-output",
            "monitoring.database_path": "./test.db",
            "google_drive.service_account_file": None,
        }.get(key)
        mock_config_class.return_value = mock_config

        # Mock auth and client with failed connection
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth

        mock_client = Mock()
        mock_client.test_connection.return_value = False
        mock_client_class.return_value = mock_client

        # Test with --test flag
        test_args = ["monitor.py", "--test", "--no-health-check"]
        with patch.object(sys, "argv", test_args):
            result = main()

        assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])