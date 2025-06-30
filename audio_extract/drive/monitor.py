"""Drive monitoring service for continuous checking of new recordings."""

import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Union

from ..tracker import ProcessingTracker
from ..extractor import AudioExtractor
from ..storage import StorageAdapter
from .client import DriveClient
from .auth import DriveAuth

logger = logging.getLogger(__name__)


class DriveMonitor:
    """Monitor Google Drive for new Meet recordings."""

    def __init__(
        self,
        tracker: ProcessingTracker,
        extractor: AudioExtractor,
        storage: StorageAdapter,
        drive_client: Optional[DriveClient] = None,
        check_interval: int = 300,  # 5 minutes
        download_temp_dir: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,  # Deprecated, kept for compatibility
    ):
        """Initialize Drive monitor.

        Args:
            tracker: Processing tracker instance
            extractor: Audio extractor instance
            storage: Storage adapter for saving extracted audio
            drive_client: Optional Drive client (creates new if not provided)
            check_interval: Seconds between checks
            download_temp_dir: Temporary directory for downloads
            output_dir: Deprecated - use storage adapter instead
        """
        self.tracker = tracker
        self.extractor = extractor
        self.storage = storage

        self.client = drive_client or DriveClient()
        self.check_interval = check_interval

        # Set up temp directory
        if download_temp_dir:
            self.temp_dir = Path(download_temp_dir)
        else:
            # Use system temp if no output_dir provided
            import tempfile

            self.temp_dir = Path(tempfile.gettempdir()) / "audio_extract"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.running = False
        self._stats = {
            "total_found": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_skipped": 0,
        }

    def find_new_recordings(self, folder_id: str, days_back: int = 7) -> List[Dict]:
        """Find recordings that haven't been processed yet.

        Args:
            folder_id: Google Drive folder ID
            days_back: How many days back to search

        Returns:
            List of unprocessed recording metadata
        """
        # Get all Meet recordings
        all_recordings = self.client.find_meet_recordings(folder_id, days_back)

        # Filter out already processed
        new_recordings = []
        for recording in all_recordings:
            file_id = recording["id"]
            if not self.tracker.is_drive_file_processed(file_id):
                new_recordings.append(recording)

        logger.info(
            f"Found {len(all_recordings)} total recordings, " f"{len(new_recordings)} are new"
        )

        return new_recordings

    def process_recording(self, file_metadata: Dict) -> bool:
        """Download and process a single recording.

        Args:
            file_metadata: Google Drive file metadata

        Returns:
            bool: True if successful
        """
        file_id = file_metadata["id"]
        file_name = file_metadata["name"]

        logger.info(f"Processing: {file_name} (ID: {file_id})")

        # Set up paths
        temp_video = self.temp_dir / f"{file_id}.mp4"
        audio_name = Path(file_name).stem + "_audio.mp3"
        temp_audio = self.temp_dir / audio_name

        # Download video
        logger.info("Downloading video...")
        self.client.download_file(file_id, temp_video)

        # Extract audio to temp location
        logger.info("Extracting audio...")
        self.extractor.extract(temp_video, temp_audio)

        # Save to storage and get URL
        logger.info("Saving to storage...")
        # Organize by date for better structure
        date_prefix = datetime.now().strftime("%Y/%m")
        storage_path = f"audio/{date_prefix}/{audio_name}"
        storage_result = self.storage.save(temp_audio, storage_path)
        storage_url = (
            storage_result.get("url", "")
            if isinstance(storage_result, dict)
            else str(storage_result)
        )

        # Mark as processed with storage info
        self.tracker.mark_drive_file_processed(
            file_id,
            status="completed",
            metadata={
                "id": file_id,
                "file_name": file_name,
                "name": file_name,
                "audio_path": storage_path,
                "storage_path": storage_path,
                "storage_url": storage_url,
                "storage_type": self.storage.__class__.__name__,
                "file_size": file_metadata.get("size"),
                "size": file_metadata.get("size"),
                "mimeType": file_metadata.get("mimeType"),
                "parents": file_metadata.get("parents"),
                "modifiedTime": file_metadata.get("modifiedTime"),
                "modified_time": file_metadata.get("modifiedTime"),
                "processed_at": datetime.now().isoformat(),
            },
        )

        # Clean up temp audio file
        if temp_audio.exists():
            temp_audio.unlink()
            logger.debug("Cleaned up temporary audio file")

        # Clean up temp file
        if temp_video.exists():
            temp_video.unlink()
            logger.debug("Cleaned up temporary video file")

        logger.info(f"Successfully processed: {file_name}")
        return True

    def check_once(self, folder_id: str, days_back: int = 7) -> Dict[str, Union[int, float]]:
        """Run one check cycle.

        Args:
            folder_id: Google Drive folder ID
            days_back: How many days back to check

        Returns:
            Statistics dictionary
        """
        logger.info("Starting check cycle")
        start_time = time.time()

        # Find new recordings
        new_recordings = self.find_new_recordings(folder_id, days_back)

        # Process each one
        processed = 0
        failed = 0

        for recording in new_recordings:
            if self.process_recording(recording):
                processed += 1
                self._stats["total_processed"] += 1
            else:
                failed += 1
                self._stats["total_failed"] += 1

        # Update stats
        self._stats["total_found"] += len(new_recordings)
        duration = time.time() - start_time

        cycle_stats = {
            "found": len(new_recordings),
            "processed": processed,
            "failed": failed,
            "duration": duration,
        }

        logger.info(
            f"Check cycle complete: found={len(new_recordings)}, "
            f"processed={processed}, failed={failed}, "
            f"duration={duration:.1f}s"
        )

        return cycle_stats

    def monitor(
        self, folder_id: str, days_back: int = 7, callback: Optional[Callable[[Dict], None]] = None
    ):
        """Monitor continuously until stopped.

        Args:
            folder_id: Google Drive folder ID
            days_back: How many days back to check
            callback: Optional callback for each cycle
        """
        logger.info(
            f"Starting Drive monitoring: folder_id={folder_id}, " f"interval={self.check_interval}s"
        )

        # Test connection first
        if not self.client.test_connection():
            raise RuntimeError("Failed to connect to Google Drive API")

        self.running = True

        while self.running:
            # Run check cycle
            cycle_stats = self.check_once(folder_id, days_back)

            # Call callback if provided
            if callback:
                callback(cycle_stats)

            # Wait for next cycle with interruptible sleep
            if self.running:
                logger.info(f"Waiting {self.check_interval}s until next check...")
                # Use small sleep intervals so we can check self.running frequently
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)  # Sleep 1 second at a time

        self.running = False
        logger.info("Monitoring stopped")

    def stop(self):
        """Stop monitoring."""
        logger.info("Stopping monitor...")
        self.running = False

    def get_stats(self) -> Dict[str, int]:
        """Get monitoring statistics.

        Returns:
            Statistics dictionary
        """
        return self._stats.copy()
