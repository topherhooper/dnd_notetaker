"""Tests for storage abstraction layer."""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta
import json

from audio_extract.storage import (
    StorageAdapter,
    LocalStorageAdapter,
    GCSStorageAdapter,
    StorageFactory,
    StorageError,
)


class TestStorageAdapter(unittest.TestCase):
    """Test the abstract StorageAdapter interface."""

    def test_interface_methods(self):
        """Test that StorageAdapter defines required interface."""
        # StorageAdapter should be abstract
        with self.assertRaises(TypeError):
            StorageAdapter()

        # Check required methods exist
        required_methods = ["save", "exists", "get_url", "delete", "list_files"]
        for method in required_methods:
            self.assertTrue(hasattr(StorageAdapter, method))


class TestLocalStorageAdapter(unittest.TestCase):
    """Test LocalStorageAdapter implementation."""

    def setUp(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = LocalStorageAdapter(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_save_file(self):
        """Test saving a file locally."""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_input.txt"
        test_file.write_text("test content")

        # Save it
        remote_path = "audio/2025/01/test.txt"
        result = self.storage.save(test_file, remote_path)

        # Check file exists at expected location
        expected_path = Path(self.temp_dir) / remote_path
        self.assertTrue(expected_path.exists())
        self.assertEqual(expected_path.read_text(), "test content")
        self.assertEqual(result["path"], str(expected_path))
        self.assertEqual(result["url"], f"file://{expected_path}")

    def test_save_creates_directories(self):
        """Test that save creates parent directories."""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("content")

        # Save to nested path
        result = self.storage.save(test_file, "deep/nested/path/file.txt")

        # Check directories were created
        expected_path = Path(self.temp_dir) / "deep/nested/path/file.txt"
        self.assertTrue(expected_path.exists())
        self.assertTrue(expected_path.parent.exists())

    def test_exists(self):
        """Test checking if file exists."""
        # Create a file
        test_path = Path(self.temp_dir) / "exists.txt"
        test_path.write_text("exists")

        # Test exists
        self.assertTrue(self.storage.exists("exists.txt"))
        self.assertFalse(self.storage.exists("not_exists.txt"))

    def test_get_url(self):
        """Test getting file URL."""
        # Create a file
        test_path = Path(self.temp_dir) / "audio/file.mp3"
        test_path.parent.mkdir(parents=True)
        test_path.write_text("audio")

        # Get URL
        url = self.storage.get_url("audio/file.mp3")
        self.assertEqual(url, f"file://{test_path}")

    def test_delete(self):
        """Test deleting a file."""
        # Create a file
        test_path = Path(self.temp_dir) / "delete_me.txt"
        test_path.write_text("delete")

        # Delete it
        self.storage.delete("delete_me.txt")
        self.assertFalse(test_path.exists())

    def test_delete_nonexistent(self):
        """Test deleting non-existent file doesn't raise error."""
        # Should not raise
        self.storage.delete("not_exists.txt")

    def test_list_files(self):
        """Test listing files with prefix."""
        # Create some files
        (Path(self.temp_dir) / "audio/2025/01").mkdir(parents=True)
        (Path(self.temp_dir) / "audio/2025/02").mkdir(parents=True)

        files = [
            "audio/2025/01/file1.mp3",
            "audio/2025/01/file2.mp3",
            "audio/2025/02/file3.mp3",
            "other/file4.mp3",
        ]

        for f in files:
            path = Path(self.temp_dir) / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("content")

        # List with prefix
        jan_files = self.storage.list_files("audio/2025/01/")
        self.assertEqual(len(jan_files), 2)
        self.assertIn("audio/2025/01/file1.mp3", jan_files)
        self.assertIn("audio/2025/01/file2.mp3", jan_files)

        # List all audio files
        audio_files = self.storage.list_files("audio/")
        self.assertEqual(len(audio_files), 3)


class TestGCSStorageAdapter(unittest.TestCase):
    """Test GCSStorageAdapter implementation."""

    def setUp(self):
        """Set up mocks for GCS client."""
        self.mock_client = Mock()
        self.mock_bucket = Mock()
        self.mock_client.bucket.return_value = self.mock_bucket

        # Mock the bucket exists check
        self.mock_bucket.exists.return_value = True

        # Patch HAS_GCS to True
        self.has_gcs_patcher = patch("audio_extract.storage.gcs_storage.HAS_GCS", True)
        self.has_gcs_patcher.start()

        # Patch the storage client
        self.patcher = patch("audio_extract.storage.gcs_storage.storage")
        self.mock_storage_module = self.patcher.start()
        self.mock_storage_module.Client.from_service_account_json.return_value = self.mock_client

        self.storage = GCSStorageAdapter(
            bucket_name="test-bucket", credentials_path="/path/to/creds.json"
        )

    def tearDown(self):
        """Stop patches."""
        self.patcher.stop()
        self.has_gcs_patcher.stop()

    def test_initialization(self):
        """Test GCS adapter initialization."""
        # Check client was created with credentials
        self.mock_storage_module.Client.from_service_account_json.assert_called_once_with(
            "/path/to/creds.json"
        )
        # Check bucket was accessed
        self.mock_client.bucket.assert_called_once_with("test-bucket")

    def test_save_file(self):
        """Test saving file to GCS."""
        # Create mock blob
        mock_blob = Mock()
        self.mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = "https://storage.googleapis.com/test-bucket/audio/test.mp3"

        # Create test file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test audio content")
            tmp_path = tmp.name

        try:
            # Save file
            result = self.storage.save(Path(tmp_path), "audio/test.mp3")

            # Check blob was created and uploaded
            self.mock_bucket.blob.assert_called_once_with("audio/test.mp3")
            mock_blob.upload_from_filename.assert_called_once_with(tmp_path)

            # Check result
            self.assertEqual(result["path"], "audio/test.mp3")
            self.assertEqual(result["url"], mock_blob.public_url)
            self.assertIn("size", result)
            self.assertIn("upload_time", result)
        finally:
            Path(tmp_path).unlink()

    def test_exists(self):
        """Test checking if blob exists in GCS."""
        mock_blob = Mock()
        self.mock_bucket.blob.return_value = mock_blob

        # Test exists = True
        mock_blob.exists.return_value = True
        self.assertTrue(self.storage.exists("audio/file.mp3"))

        # Test exists = False
        mock_blob.exists.return_value = False
        self.assertFalse(self.storage.exists("audio/not_found.mp3"))

    def test_get_url_public(self):
        """Test getting public URL."""
        self.storage.public_access = True
        mock_blob = Mock()
        self.mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = "https://storage.googleapis.com/test-bucket/audio/file.mp3"

        url = self.storage.get_url("audio/file.mp3")
        self.assertEqual(url, mock_blob.public_url)

    def test_get_url_signed(self):
        """Test getting signed URL."""
        self.storage.public_access = False
        self.storage.url_expiration_hours = 24

        mock_blob = Mock()
        self.mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed-url"

        url = self.storage.get_url("audio/file.mp3")

        # Check signed URL was generated
        mock_blob.generate_signed_url.assert_called_once()
        call_args = mock_blob.generate_signed_url.call_args[0]
        self.assertIsInstance(call_args[0], timedelta)
        self.assertEqual(url, "https://signed-url")

    def test_delete(self):
        """Test deleting blob from GCS."""
        mock_blob = Mock()
        self.mock_bucket.blob.return_value = mock_blob

        self.storage.delete("audio/file.mp3")

        mock_blob.delete.assert_called_once()

    def test_list_files(self):
        """Test listing files with prefix."""
        # Create mock blobs with proper name attribute
        mock_blobs = []
        for name in [
            "audio/2025/01/file1.mp3",
            "audio/2025/01/file2.mp3",
            "audio/2025/01/file3.mp3",
        ]:
            blob = Mock()
            blob.name = name
            mock_blobs.append(blob)

        self.mock_client.list_blobs.return_value = mock_blobs

        files = self.storage.list_files("audio/2025/01/")

        # Check list_blobs was called with prefix
        self.mock_client.list_blobs.assert_called_once_with(
            self.mock_bucket, prefix="audio/2025/01/"
        )

        # Check returned file names
        self.assertEqual(len(files), 3)
        self.assertEqual(
            files, ["audio/2025/01/file1.mp3", "audio/2025/01/file2.mp3", "audio/2025/01/file3.mp3"]
        )


class TestStorageFactory(unittest.TestCase):
    """Test StorageFactory for creating storage adapters."""

    def test_create_local_storage(self):
        """Test creating local storage adapter."""
        config = {"type": "local", "local": {"path": "/tmp/audio"}}

        storage = StorageFactory.create(config)
        self.assertIsInstance(storage, LocalStorageAdapter)
        self.assertEqual(storage.base_path, Path("/tmp/audio"))

    def test_create_gcs_storage(self):
        """Test creating GCS storage adapter."""
        with patch("audio_extract.storage.gcs_storage.HAS_GCS", True), patch(
            "audio_extract.storage.gcs_storage.storage"
        ) as mock_storage:
            mock_client = Mock()
            mock_bucket = Mock()
            mock_bucket.exists.return_value = True
            mock_client.bucket.return_value = mock_bucket
            mock_storage.Client.from_service_account_json.return_value = mock_client
            config = {
                "type": "gcs",
                "gcs": {
                    "bucket_name": "my-bucket",
                    "credentials_path": "/path/to/creds.json",
                    "public_access": False,
                    "url_expiration_hours": 48,
                },
            }

            storage = StorageFactory.create(config)
            self.assertIsInstance(storage, GCSStorageAdapter)
            self.assertEqual(storage.bucket_name, "my-bucket")
            self.assertEqual(storage.url_expiration_hours, 48)

    def test_create_invalid_type(self):
        """Test creating storage with invalid type raises error."""
        config = {"type": "invalid", "invalid": {}}

        with self.assertRaises(ValueError) as ctx:
            StorageFactory.create(config)
        self.assertIn("Unsupported storage type", str(ctx.exception))

    def test_create_with_defaults(self):
        """Test creating storage with minimal config uses defaults."""
        # Local with defaults
        config = {"type": "local"}
        storage = StorageFactory.create(config)
        self.assertEqual(storage.base_path, Path("./output"))

        # GCS with defaults
        with patch("audio_extract.storage.gcs_storage.HAS_GCS", True), patch(
            "audio_extract.storage.gcs_storage.storage"
        ) as mock_storage:
            mock_client = Mock()
            mock_bucket = Mock()
            mock_bucket.exists.return_value = True
            mock_client.bucket.return_value = mock_bucket
            mock_storage.Client.from_service_account_json.return_value = mock_client
            config = {
                "type": "gcs",
                "gcs": {"bucket_name": "my-bucket", "credentials_path": "/creds.json"},
            }
            storage = StorageFactory.create(config)
            self.assertTrue(storage.public_access)  # default
            self.assertEqual(storage.url_expiration_hours, 24)  # default


if __name__ == "__main__":
    unittest.main()
