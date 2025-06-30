"""Tests for dashboard storage URL functionality."""

import json
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
import urllib.request

from audio_extract.dashboard.server import DashboardHandler
from audio_extract.tracker import ProcessingTracker
from http.server import HTTPServer
from threading import Thread
import time


class TestDashboardStorageURLs(unittest.TestCase):
    """Test dashboard storage URL features."""

    def setUp(self):
        """Set up test environment."""
        import random
        self.port = random.randint(10000, 20000)
        self.server = None
        self.server_thread = None
        
        # Create a temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize tracker and add test data
        self.tracker = ProcessingTracker(Path(self.temp_db.name))
        
        # Add some test data with storage URLs
        self.tracker.mark_processed(
            "test_video1.mp4",
            status="completed",
            metadata={
                "storage_url": "https://storage.googleapis.com/bucket/audio/test1.mp3",
                "storage_path": "audio/2025/01/test1.mp3",
                "storage_type": "GCSStorageAdapter",
                "duration": 120
            }
        )
        
        self.tracker.mark_processed(
            "test_video2.mp4",
            status="completed",
            metadata={
                "storage_url": "https://storage.googleapis.com/bucket/audio/test2.mp3",
                "storage_path": "audio/2025/01/test2.mp3",
                "storage_type": "GCSStorageAdapter",
                "duration": 180
            }
        )
        
        self.tracker.mark_processed(
            "test_video3.mp4",
            status="failed",
            metadata={
                "error": "Extraction failed",
                "storage_path": "audio/2025/01/test3.mp3",
                "storage_type": "GCSStorageAdapter"
            }
        )
        
        self.tracker.close()

    def tearDown(self):
        """Clean up test environment."""
        if self.server:
            self.server.shutdown()
            if hasattr(self.server, 'server_close'):
                self.server.server_close()
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        # Clean up temp database
        Path(self.temp_db.name).unlink(missing_ok=True)

    def start_test_server(self, storage_config=None):
        """Start test server."""
        def handler_class(*args, **kwargs):
            return DashboardHandler(*args, tracker_db=self.temp_db.name, storage_config=storage_config, **kwargs)
        
        self.server = HTTPServer(("", self.port), handler_class)
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.5)

    def test_recent_includes_storage_urls(self):
        """Test that recent endpoint includes storage URLs."""
        self.start_test_server()
        
        url = f"http://localhost:{self.port}/api/recent?days=7"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        # Should have 2 completed videos
        self.assertEqual(len(data), 3)  # All videos, not just completed
        
        # Check that storage URLs are included
        for item in data:
            if item["status"] == "completed":
                self.assertIn("storage_url", item)
                self.assertIn("storage_path", item)
                self.assertIn("storage_type", item)
                self.assertTrue(item["storage_url"].startswith("https://"))

    def test_failed_includes_storage_info(self):
        """Test that failed endpoint includes storage info."""
        self.start_test_server()
        
        url = f"http://localhost:{self.port}/api/failed"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        # Should have 1 failed video
        self.assertEqual(len(data), 1)
        
        failed = data[0]
        self.assertIn("storage_path", failed)
        self.assertIn("storage_type", failed)
        # Failed videos might not have storage_url
        self.assertIn("storage_url", failed)

    def test_refresh_url_endpoint(self):
        """Test URL refresh endpoint."""
        # Mock storage configuration
        storage_config = {
            "type": "gcs",
            "bucket_name": "test-bucket",
            "credentials_path": "/fake/path.json"
        }
        
        with patch('audio_extract.storage.StorageFactory.create') as mock_factory:
            # Mock storage adapter
            mock_storage = MagicMock()
            mock_storage.get_url.return_value = "https://storage.googleapis.com/bucket/audio/test1.mp3?signed=new"
            mock_factory.return_value = mock_storage
            
            self.start_test_server(storage_config=storage_config)
            
            # Test refresh URL
            url = f"http://localhost:{self.port}/api/refresh-url"
            data = json.dumps({"storage_path": "audio/2025/01/test1.mp3"}).encode()
            
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            
            self.assertIn("url", result)
            self.assertIn("signed=new", result["url"])
            mock_storage.get_url.assert_called_once_with("audio/2025/01/test1.mp3")


if __name__ == "__main__":
    unittest.main()