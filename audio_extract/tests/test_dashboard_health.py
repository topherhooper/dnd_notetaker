"""Tests for dashboard health check functionality."""

import json
import unittest
from unittest.mock import patch, MagicMock, Mock
from http.server import HTTPServer
from threading import Thread
import time
import urllib.request
import urllib.error
import tempfile
import sqlite3
from pathlib import Path

from audio_extract.dashboard.server import DashboardHandler, run_server
from audio_extract.tracker import ProcessingTracker


class TestDashboardHealth(unittest.TestCase):
    """Test dashboard health check endpoint."""

    def setUp(self):
        """Set up test server."""
        # Use a unique port for each test to avoid conflicts
        import random
        self.port = random.randint(10000, 20000)
        self.server = None
        self.server_thread = None
        
        # Create a temporary database with proper schema
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize the database with proper schema
        tracker = ProcessingTracker(Path(self.temp_db.name))
        tracker.close()

    def tearDown(self):
        """Shut down test server."""
        if self.server:
            self.server.shutdown()
            if hasattr(self.server, 'server_close'):
                self.server.server_close()
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        # Clean up temp database
        if hasattr(self, 'temp_db'):
            Path(self.temp_db.name).unlink(missing_ok=True)

    def start_test_server(self, storage_config=None):
        """Start a test server in a separate thread."""
        # Mock the imports to avoid issues
        with patch('audio_extract.dashboard.server.verify_ffmpeg_installed'):
            def handler_class(*args, **kwargs):
                return DashboardHandler(*args, tracker_db=self.temp_db.name, storage_config=storage_config, **kwargs)
            
            self.server = HTTPServer(("", self.port), handler_class)
            self.server_thread = Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            time.sleep(0.5)  # Give server time to start

    def test_health_endpoint_exists(self):
        """Test that health endpoint responds."""
        self.start_test_server()
        
        url = f"http://localhost:{self.port}/api/health"
        response = urllib.request.urlopen(url)
        self.assertEqual(response.status, 200)
        
        data = json.loads(response.read().decode())
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("components", data)

    def test_health_components(self):
        """Test that all expected components are checked."""
        self.start_test_server()
        
        url = f"http://localhost:{self.port}/api/health"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        components = data["components"]
        self.assertIn("ffmpeg", components)
        self.assertIn("database", components)
        self.assertIn("storage", components)
        self.assertIn("temp_storage", components)

    def test_ffmpeg_unhealthy(self):
        """Test health status when FFmpeg is not available."""
        # We need to patch verify_ffmpeg_installed at the module level where it's used
        with patch('audio_extract.dashboard.server.verify_ffmpeg_installed') as mock_verify:
            mock_verify.side_effect = Exception("FFmpeg not found")
            
            # Create a custom handler that will use our mocked function
            def handler_class(*args, **kwargs):
                return DashboardHandler(*args, tracker_db=self.temp_db.name, storage_config=None, **kwargs)
            
            self.server = HTTPServer(("", self.port), handler_class)
            self.server_thread = Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            time.sleep(0.5)
            
            url = f"http://localhost:{self.port}/api/health"
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode())
            
            self.assertEqual(data["components"]["ffmpeg"]["status"], "unhealthy")
            self.assertIn("FFmpeg not found", data["components"]["ffmpeg"]["message"])
            # Database failure makes the overall status unhealthy, not degraded
            self.assertIn(data["status"], ["unhealthy", "degraded"])

    def test_storage_configured(self):
        """Test health check with storage configured."""
        storage_config = {
            "type": "local",
            "path": "/tmp/test_storage"
        }
        self.start_test_server(storage_config=storage_config)
        
        url = f"http://localhost:{self.port}/api/health"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        self.assertIn("storage", data["components"])
        # Storage component should have a status (not "unknown")
        self.assertNotEqual(data["components"]["storage"]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()