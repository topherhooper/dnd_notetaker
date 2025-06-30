#!/usr/bin/env python3
"""CLI for Google Drive monitoring."""

import sys
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_extract.config import Config  # noqa: E402
from audio_extract.tracker import ProcessingTracker  # noqa: E402
from audio_extract.extractor import AudioExtractor  # noqa: E402
from audio_extract.drive import DriveAuth, DriveClient  # noqa: E402
from audio_extract.drive.storage_monitor import StorageAwareDriveMonitor  # noqa: E402
from audio_extract.storage import StorageFactory  # noqa: E402


def setup_logging(level: str = "INFO"):
    """Set up logging configuration."""
    import colorlog

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )
    logging.basicConfig(level=level, handlers=[handler])


def handle_cycle_stats(stats: dict):
    """Callback to handle monitoring cycle statistics."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"\n[{timestamp}] Cycle complete: "
        f"found={stats['found']}, "
        f"processed={stats['processed']}, "
        f"failed={stats['failed']}, "
        f"duration={stats['duration']:.1f}s"
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Monitor Google Drive for new Meet recordings")

    # Configuration options
    parser.add_argument(
        "--config", "-c", type=str, help="Path to configuration file (YAML or JSON)"
    )
    parser.add_argument("--folder-id", "-f", type=str, help="Google Drive folder ID to monitor")
    parser.add_argument("--output", "-o", type=str, help="Output directory for extracted audio")
    parser.add_argument(
        "--interval", "-i", type=int, default=300, help="Check interval in seconds (default: 300)"
    )
    parser.add_argument(
        "--days-back", "-d", type=int, default=7, help="Number of days to look back (default: 7)"
    )

    # Authentication options
    parser.add_argument("--credentials", type=str, help="Path to service account JSON file")

    # Monitoring options
    parser.add_argument("--once", action="store_true", help="Run one check cycle and exit")
    parser.add_argument("--test", action="store_true", help="Test connection and exit")

    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    # Health check options
    parser.add_argument(
        "--health-port",
        type=int,
        default=8081,
        help="Port for health check endpoint (default: 8081)",
    )
    parser.add_argument(
        "--no-health-check", action="store_true", help="Disable health check endpoint"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = Config(args.config)

    # Apply command-line overrides
    if args.folder_id:
        config.set("google_drive.recordings_folder_id", args.folder_id)
    if args.output:
        config.set("processing.output_directory", args.output)
    if args.interval:
        config.set("google_drive.check_interval_seconds", args.interval)
    if args.credentials:
        config.set("google_drive.service_account_file", args.credentials)

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1

    # Get configuration values
    folder_id = config.get("google_drive.recordings_folder_id")
    output_dir = config.get("processing.output_directory")
    db_path = config.get("monitoring.database_path")

    logger.info(f"Folder ID: {folder_id}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Database: {db_path}")

    # Initialize components
    auth = DriveAuth(config.get("google_drive.service_account_file"))
    client = DriveClient(auth)

    # Test connection if requested
    if args.test:
        logger.info("Testing Google Drive connection...")
        if client.test_connection():
            logger.info("✅ Connection successful!")

            # Try to list files in the folder
            logger.info(f"Checking folder: {folder_id}")
            files = client.list_files(folder_id, page_size=5)
            logger.info(f"Found {len(files)} files in folder")
            for file in files[:5]:
                logger.info(f"  - {file['name']}")

            return 0
        else:
            logger.error("❌ Connection failed!")
            return 1

    # Initialize processing components first
    tracker = ProcessingTracker(db_path)
    extractor = AudioExtractor(
        bitrate=config.get("processing.audio_format.bitrate"),
        sample_rate=config.get("processing.audio_format.sample_rate"),
        channels=config.get("processing.audio_format.channels"),
    )

    # Create storage adapter from config
    storage_config = config.get("storage", {})
    if not storage_config or not storage_config.get("type"):
        # Default to local storage if not configured
        storage_config = {"type": "local", "local": {"path": output_dir}}

    # Create storage adapter
    storage = StorageFactory.create(storage_config)
    logger.info(f"Using {storage_config['type']} storage")

    # Start health check server if enabled
    health_thread = None
    if not args.no_health_check:
        logger.info(f"Starting health check server on port {args.health_port}")

        from ..health import init_health_checker, run_health_server
        import threading

        # Initialize health checker with components
        init_health_checker(tracker=tracker, drive_client=client, storage_config=storage_config)

        # Start health server in background thread
        health_thread = threading.Thread(
            target=run_health_server, args=(args.health_port,), daemon=True
        )
        health_thread.start()

        logger.info(
            f"Health check endpoint available at http://localhost:{args.health_port}/health"
        )

    # Start dashboard if enabled
    dashboard_thread = None
    if config.get("monitoring.enable_dashboard"):
        dashboard_port = config.get("monitoring.dashboard_port", 8080)
        logger.info(f"Starting web dashboard on port {dashboard_port}")

        # Import and start dashboard in a separate thread
        from ..dashboard.server import run_server
        import threading

        dashboard_thread = threading.Thread(
            target=run_server, args=(dashboard_port, db_path), daemon=True
        )
        dashboard_thread.start()

        # Give it a moment to start
        import time

        time.sleep(1)

        logger.info(f"Dashboard available at http://localhost:{dashboard_port}")

        # Open browser if configured
        if config.get("monitoring.dashboard_open_browser"):
            import webbrowser

            webbrowser.open(f"http://localhost:{dashboard_port}")


    # Always use storage-aware monitor for consistency
    monitor = StorageAwareDriveMonitor(
        tracker=tracker,
        extractor=extractor,
        storage=storage,
        output_dir=output_dir,
        drive_client=client,
        check_interval=args.interval,
        delete_local_after_upload=config.get("processing.delete_local_after_upload", False),
    )

    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("\nReceived interrupt signal, stopping...")
        monitor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run monitoring
    if args.once:
        logger.info("Running single check cycle...")
        stats = monitor.check_once(folder_id, args.days_back)
        handle_cycle_stats(stats)
    else:
        logger.info("Starting continuous monitoring...")
        logger.info("Press Ctrl+C to stop")
        monitor.monitor(folder_id, days_back=args.days_back, callback=handle_cycle_stats)

    # Print final statistics
    final_stats = monitor.get_stats()
    logger.info("\nFinal statistics:")
    logger.info(f"  Total found: {final_stats['total_found']}")
    logger.info(f"  Total processed: {final_stats['total_processed']}")
    logger.info(f"  Total failed: {final_stats['total_failed']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
