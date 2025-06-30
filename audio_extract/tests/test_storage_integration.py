"""Integration tests for storage with audio extraction."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from audio_extract.drive.monitor import DriveMonitor
from audio_extract.drive.storage_monitor import StorageAwareDriveMonitor
from audio_extract.tracker import ProcessingTracker
from audio_extract.extractor import AudioExtractor
from audio_extract.storage import StorageFactory, LocalStorageAdapter


class TestStorageIntegration(unittest.TestCase):
    """Test storage integration with Drive monitor."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()

        # Create real tracker
        self.tracker = ProcessingTracker(self.db_path)

        # Mock extractor
        self.mock_extractor = Mock(spec=AudioExtractor)

        # Create storage
        self.storage_config = {"type": "local", "local": {"path": str(self.output_dir)}}
        self.storage = StorageFactory.create(self.storage_config)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_monitor_with_storage(self):
        """Test that monitor can work with storage abstraction."""
        # Create monitor with storage-aware configuration
        monitor = StorageAwareDriveMonitor(
            tracker=self.tracker,
            extractor=self.mock_extractor,
            storage=self.storage,
            output_dir=self.output_dir,
            drive_client=Mock(),
        )

        # Mock file metadata
        file_metadata = {
            "id": "test-file-id",
            "name": "meeting_2025-01-29.mp4",
            "size": "1000000",
            "modifiedTime": "2025-01-29T10:00:00Z",
            "mimeType": "video/mp4",
            "parents": ["folder123"],
        }

        # Mock download
        monitor.client.download_file = Mock()

        # Mock extract to create output file
        def create_audio(video_path, audio_path):
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_text("test audio")

        # Process recording
        with patch.object(monitor.extractor, "extract", side_effect=create_audio) as mock_extract:
            result = monitor.process_recording(file_metadata)

        # Verify extraction was called
        self.assertTrue(result)
        mock_extract.assert_called_once()

        # Verify file was tracked
        self.assertTrue(self.tracker.is_drive_file_processed("test-file-id"))

    def test_storage_url_in_metadata(self):
        """Test that storage URL is saved in tracker metadata."""
        # Create monitor
        monitor = StorageAwareDriveMonitor(
            tracker=self.tracker,
            extractor=self.mock_extractor,
            storage=self.storage,
            output_dir=self.output_dir,
            drive_client=Mock(),
            delete_local_after_upload=False,
        )

        # Mock file metadata
        file_metadata = {
            "id": "test-storage-id",
            "name": "meeting_storage_test.mp4",
            "size": "2000000",
            "modifiedTime": "2025-01-29T14:00:00Z",
            "mimeType": "video/mp4",
            "parents": ["folder123"],
        }

        # Create a dummy audio file that will be "extracted"
        dummy_audio = self.output_dir / "meeting_storage_test_audio.mp3"
        dummy_audio.write_text("fake audio content")

        # Mock the extractor to create the file
        def mock_extract(video_path, audio_path):
            audio_path.write_text("fake audio content")

        self.mock_extractor.extract.side_effect = mock_extract

        # Mock download
        monitor.client.download_file = Mock()

        # Process recording
        result = monitor.process_recording(file_metadata)
        self.assertTrue(result)

        # Get metadata from tracker
        metadata = self.tracker.get_drive_file_metadata("test-storage-id")
        self.assertIsNotNone(metadata)

        # Check storage-related fields
        stored_meta = metadata["metadata"]
        self.assertIn("storage_url", stored_meta)
        self.assertIn("storage_path", stored_meta)
        self.assertIn("storage_type", stored_meta)
        self.assertTrue(stored_meta["storage_url"].startswith("file://"))
        self.assertEqual(stored_meta["storage_type"], "LocalStorageAdapter")


class TestEnhancedMonitor(unittest.TestCase):
    """Test enhanced monitor with storage support."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    @patch("audio_extract.storage.gcs_storage.HAS_GCS", True)
    @patch("audio_extract.storage.gcs_storage.storage")
    def test_process_with_gcs_storage(self, mock_storage_module):
        """Test processing with GCS storage."""
        # Mock GCS client
        mock_client = Mock()
        mock_bucket = Mock()
        mock_bucket.exists.return_value = True
        mock_client.bucket.return_value = mock_bucket
        mock_storage_module.Client.from_service_account_json.return_value = mock_client

        # Mock blob for upload
        mock_blob = Mock()
        mock_blob.public_url = (
            "https://storage.googleapis.com/test-bucket/audio/2025/01/test_audio.mp3"
        )
        mock_bucket.blob.return_value = mock_blob

        # Create GCS storage
        gcs_config = {
            "type": "gcs",
            "gcs": {
                "bucket_name": "test-bucket",
                "credentials_path": "/fake/creds.json",
                "public_access": True,
            },
        }
        gcs_storage = StorageFactory.create(gcs_config)

        # Create components
        tracker = ProcessingTracker(self.db_path)
        mock_extractor = Mock(spec=AudioExtractor)

        # Create monitor with GCS storage
        monitor = StorageAwareDriveMonitor(
            tracker=tracker,
            extractor=mock_extractor,
            storage=gcs_storage,
            output_dir=self.output_dir,
            drive_client=Mock(),
            delete_local_after_upload=True,
        )

        # Mock file metadata
        file_metadata = {
            "id": "gcs-test-id",
            "name": "meeting_gcs_test.mp4",
            "size": "3000000",
            "modifiedTime": "2025-01-29T16:00:00Z",
            "mimeType": "video/mp4",
            "parents": ["folder456"],
        }

        # Mock the extractor to create a file
        def mock_extract(video_path, audio_path):
            audio_path.write_text("fake audio for gcs")

        mock_extractor.extract.side_effect = mock_extract
        monitor.client.download_file = Mock()

        # Process recording
        result = monitor.process_recording(file_metadata)
        self.assertTrue(result)

        # Verify GCS upload was called
        mock_blob.upload_from_filename.assert_called_once()

        # Verify local file was deleted (since delete_local_after_upload=True)
        audio_file = self.output_dir / "meeting_gcs_test_audio.mp3"
        self.assertFalse(audio_file.exists())

        # Check metadata
        metadata = tracker.get_drive_file_metadata("gcs-test-id")
        stored_meta = metadata["metadata"]
        self.assertEqual(stored_meta["storage_url"], mock_blob.public_url)
        self.assertEqual(stored_meta["storage_type"], "GCSStorageAdapter")
        self.assertIn("audio/2025", stored_meta["storage_path"])


if __name__ == "__main__":
    unittest.main()
