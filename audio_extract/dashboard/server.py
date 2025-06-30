#!/usr/bin/env python3
"""Simple web server for the audio extraction dashboard."""

import json
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# Import our tracker (when running as module)
try:
    from ..tracker import ProcessingTracker
except ImportError:
    # When running directly
    import sys

    sys.path.append(str(Path(__file__).parent.parent.parent))
    from audio_extract.tracker import ProcessingTracker
from audio_extract.storage import StorageFactory
from audio_extract.utils import verify_ffmpeg_installed


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    def __init__(self, *args, tracker_db="processed_videos.db", storage_config=None, **kwargs):
        self.tracker_db = Path(tracker_db)
        self.storage_config = storage_config or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # API endpoints
        if path.startswith("/api/"):
            self.handle_api_get(path[5:], parsed_path.query)
        # Static files
        elif path.startswith("/static/"):
            self.path = path[7:]  # Remove /static/ prefix
            self.directory = Path(__file__).parent / "static"
            super().do_GET()
        # Root - serve index.html
        elif path == "/":
            self.serve_file(Path(__file__).parent / "index.html")
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith("/api/"):
            self.handle_api_post(self.path[5:])
        else:
            self.send_error(404)

    def handle_api_get(self, endpoint, query):
        """Handle API GET requests."""
        # Create a new tracker for each request to ensure fresh data
        # Note: This will trigger migration check, but it's already optimized
        # to only log when actual migrations are needed
        tracker = ProcessingTracker(self.tracker_db)
        
        try:
            if endpoint == "stats":
                data = tracker.get_statistics()
            elif endpoint == "recent":
                params = urllib.parse.parse_qs(query)
                days = int(params.get("days", [7])[0])
                data = tracker.get_recent_processed(days=days)
                # Extract storage URLs from metadata
                for item in data:
                    if item.get("metadata"):
                        item["storage_url"] = item["metadata"].get("storage_url", "")
                        item["storage_path"] = item["metadata"].get("storage_path", "")
                        item["storage_type"] = item["metadata"].get("storage_type", "")
            elif endpoint == "failed":
                data = tracker.get_failed_videos()
                # Extract storage URLs from metadata  
                for item in data:
                    if item.get("metadata"):
                        item["storage_url"] = item["metadata"].get("storage_url", "")
                        item["storage_path"] = item["metadata"].get("storage_path", "")
                        item["storage_type"] = item["metadata"].get("storage_type", "")
            elif endpoint == "health":
                data = self.get_health_status()
            else:
                self.send_error(404)
                return

            self.send_json_response(data)
        finally:
            tracker.close()

    def handle_api_post(self, endpoint):
        """Handle API POST requests."""
        # Read request body
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body) if body else {}

        tracker = ProcessingTracker(self.tracker_db)
        
        try:
            if endpoint == "reprocess":
                file_path = data.get("file_path")
                if file_path:
                    tracker.mark_for_reprocessing(file_path)
                    self.send_json_response({"status": "ok"})
                else:
                    self.send_error(400, "Missing file_path")

            elif endpoint == "cleanup":
                days = data.get("days", 90)
                deleted = tracker.cleanup_old_entries(days=days)
                self.send_json_response({"deleted": deleted})

            elif endpoint == "clear-failed":
                # Get all failed videos and mark for reprocessing
                failed = tracker.get_failed_videos()
                for video in failed:
                    tracker.mark_for_reprocessing(video["file_path"])
                self.send_json_response({"cleared": len(failed)})
                
            elif endpoint == "refresh-url":
                # Refresh a signed URL for a storage path
                storage_path = data.get("storage_path")
                if not storage_path:
                    self.send_error(400, "Missing storage_path")
                    return
                    
                # Try to generate a new URL if storage is configured
                if self.storage_config:
                    try:
                        storage = StorageFactory.create(self.storage_config)
                        if hasattr(storage, 'get_url'):
                            new_url = storage.get_url(storage_path)
                            self.send_json_response({"url": new_url})
                        else:
                            self.send_error(501, "Storage adapter doesn't support URL generation")
                    except Exception as e:
                        self.send_error(500, f"Failed to refresh URL: {str(e)}")
                else:
                    self.send_error(501, "No storage configured")

            else:
                self.send_error(404)
                return
        finally:
            tracker.close()

    def send_json_response(self, data):
        """Send JSON response."""

        # Custom JSON encoder to handle datetime objects
        def json_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        content = json.dumps(data, default=json_encoder).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(content))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def serve_file(self, filepath):
        """Serve a static file."""
        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        if filepath.suffix == ".html":
            self.send_header("Content-Type", "text/html")
        elif filepath.suffix == ".css":
            self.send_header("Content-Type", "text/css")
        elif filepath.suffix == ".js":
            self.send_header("Content-Type", "application/javascript")

        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Override to suppress request logging."""
        pass
    
    def get_health_status(self):
        """Get system health status."""
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check FFmpeg
        try:
            verify_ffmpeg_installed()
            health["components"]["ffmpeg"] = {
                "status": "healthy",
                "message": "FFmpeg is available"
            }
        except Exception as e:
            health["components"]["ffmpeg"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health["status"] = "degraded"
        
        # Check database
        try:
            conn = sqlite3.connect(str(self.tracker_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processed_videos")
            count = cursor.fetchone()[0]
            conn.close()
            health["components"]["database"] = {
                "status": "healthy",
                "message": f"Database accessible, {count} records"
            }
        except Exception as e:
            health["components"]["database"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health["status"] = "unhealthy"
        
        # Check storage if configured
        if self.storage_config:
            try:
                storage = StorageFactory.create(self.storage_config)
                # Try to list files (basic connectivity test)
                if hasattr(storage, 'list_files'):
                    storage.list_files("")
                health["components"]["storage"] = {
                    "status": "healthy",
                    "message": f"Storage ({type(storage).__name__}) is accessible"
                }
            except Exception as e:
                health["components"]["storage"] = {
                    "status": "unhealthy",
                    "message": str(e)
                }
                health["status"] = "degraded"
        else:
            health["components"]["storage"] = {
                "status": "unknown",
                "message": "No storage configured"
            }
        
        # Check temp directory
        try:
            temp_dir = Path("/tmp/audio_extract")
            if temp_dir.exists():
                # Check disk space (basic check)
                import shutil
                total, used, free = shutil.disk_usage("/tmp")
                free_gb = free // (1024**3)
                health["components"]["temp_storage"] = {
                    "status": "healthy" if free_gb > 1 else "warning",
                    "message": f"{free_gb}GB free in temp directory"
                }
            else:
                health["components"]["temp_storage"] = {
                    "status": "warning",
                    "message": "Temp directory not found"
                }
        except Exception as e:
            health["components"]["temp_storage"] = {
                "status": "warning",
                "message": str(e)
            }
        
        return health


def run_server(port=8080, db_path="processed_videos.db", storage_config=None):
    """Run the dashboard server."""
    # Create handler class with db_path and storage_config
    def handler_class(*args, **kwargs):
        return DashboardHandler(*args, tracker_db=db_path, storage_config=storage_config, **kwargs)

    server = HTTPServer(("", port), handler_class)
    print(f"Dashboard server running at http://localhost:{port}")
    print("Press Ctrl+C to stop")

    server.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audio Extraction Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    parser.add_argument("--db", default="processed_videos.db", help="Database path")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    run_server(args.port, args.db)
