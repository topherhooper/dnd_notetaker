"""Health check endpoint for monitoring service health."""

import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, jsonify
from .tracker import ProcessingTracker
from .drive import DriveAuth, DriveClient
from .storage import StorageFactory

logger = logging.getLogger(__name__)

app = Flask(__name__)


class HealthChecker:
    """Performs health checks on various system components."""

    def __init__(
        self,
        tracker: Optional[ProcessingTracker] = None,
        drive_client: Optional[DriveClient] = None,
        storage_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize health checker.

        Args:
            tracker: Processing tracker instance
            drive_client: Google Drive client instance
            storage_config: Storage configuration
        """
        self.tracker = tracker
        self.drive_client = drive_client
        self.storage_config = storage_config

    def check_database_connection(self) -> bool:
        """Check database connectivity."""
        if not self.tracker:
            return True  # Skip if not configured

        try:
            # Try to get statistics
            stats = self.tracker.get_statistics()
            return isinstance(stats, dict) and "total" in stats
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False

    def check_gcs_access(self) -> bool:
        """Check Google Cloud Storage access."""
        if not self.storage_config or self.storage_config.get("type") != "gcs":
            return True  # Skip if not using GCS

        try:
            storage = StorageFactory.create(self.storage_config)
            # Try to list files with a very specific prefix unlikely to match anything
            test_prefix = f"_health_check_test_{datetime.now().timestamp()}"
            files = storage.list_files(test_prefix)
            return isinstance(files, list)
        except Exception as e:
            logger.error(f"GCS check failed: {e}")
            return False

    def check_drive_access(self) -> bool:
        """Check Google Drive API access."""
        if not self.drive_client:
            return True  # Skip if not configured

        try:
            return self.drive_client.test_connection()
        except Exception as e:
            logger.error(f"Drive check failed: {e}")
            return False

    def check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg check failed: {e}")
            return False

    def perform_all_checks(self) -> Dict[str, bool]:
        """Perform all health checks.

        Returns:
            Dictionary with check results
        """
        return {
            "database": self.check_database_connection(),
            "gcs": self.check_gcs_access(),
            "drive": self.check_drive_access(),
            "ffmpeg": self.check_ffmpeg_available(),
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def init_health_checker(
    tracker: Optional[ProcessingTracker] = None,
    drive_client: Optional[DriveClient] = None,
    storage_config: Optional[Dict[str, Any]] = None,
):
    """Initialize the global health checker.

    Args:
        tracker: Processing tracker instance
        drive_client: Google Drive client instance
        storage_config: Storage configuration
    """
    global _health_checker
    _health_checker = HealthChecker(tracker, drive_client, storage_config)


@app.route("/health")
def health_check():
    """Health check endpoint for monitoring.

    Returns:
        JSON response with health status
    """
    if not _health_checker:
        # Return basic health if checker not initialized
        return (
            jsonify(
                {
                    "status": "healthy",
                    "checks": {},
                    "timestamp": datetime.now().isoformat(),
                    "message": "Health checker not fully initialized",
                }
            ),
            200,
        )

    # Perform all checks
    checks = _health_checker.perform_all_checks()

    # Determine overall status
    all_healthy = all(checks.values())
    status = "healthy" if all_healthy else "unhealthy"

    response = {"status": status, "checks": checks, "timestamp": datetime.now().isoformat()}

    # Add details for failed checks
    if not all_healthy:
        failed_checks = [name for name, healthy in checks.items() if not healthy]
        response["failed_checks"] = failed_checks
        response["message"] = f"Failed checks: {', '.join(failed_checks)}"

    # Return appropriate status code
    status_code = 200 if all_healthy else 503

    return jsonify(response), status_code


@app.route("/ready")
def readiness_check():
    """Readiness check endpoint.

    Returns:
        JSON response indicating if service is ready
    """
    if not _health_checker:
        return (
            jsonify(
                {
                    "ready": False,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Service not fully initialized",
                }
            ),
            503,
        )

    # For readiness, we check critical components only
    critical_checks = {
        "database": _health_checker.check_database_connection(),
        "drive": _health_checker.check_drive_access(),
    }

    is_ready = all(critical_checks.values())

    return jsonify(
        {"ready": is_ready, "checks": critical_checks, "timestamp": datetime.now().isoformat()}
    ), (200 if is_ready else 503)


@app.route("/live")
def liveness_check():
    """Liveness check endpoint.

    Returns:
        Simple response indicating service is alive
    """
    return jsonify({"alive": True, "timestamp": datetime.now().isoformat()}), 200


def run_health_server(port: int = 8081):
    """Run the health check server.

    Args:
        port: Port to run server on
    """
    logger.info(f"Starting health check server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
