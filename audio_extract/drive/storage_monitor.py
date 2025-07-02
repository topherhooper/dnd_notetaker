"""Enhanced Drive monitor with storage abstraction support."""

import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union

from ..tracker import ProcessingTracker
from ..extractor import AudioExtractor
from ..storage import StorageAdapter, StorageFactory
from .client import DriveClient
from .monitor import DriveMonitor

logger = logging.getLogger(__name__)


class StorageAwareDriveMonitor(DriveMonitor):
    """Drive monitor that uploads extracted audio to configured storage."""

    def __init__(
        self,
        tracker: ProcessingTracker,
        extractor: AudioExtractor,
        storage: StorageAdapter,
        output_dir: Union[str, Path],
        drive_client: Optional[DriveClient] = None,
        check_interval: int = 300,
        download_temp_dir: Optional[Union[str, Path]] = None,
        delete_local_after_upload: bool = True,
    ):
        """Initialize storage-aware Drive monitor.

        Args:
            tracker: Processing tracker
            extractor: Audio extractor
            storage: Storage adapter for uploading audio files
            output_dir: Local output directory (temporary if using cloud storage)
            drive_client: Google Drive client
            check_interval: Check interval in seconds
            download_temp_dir: Temporary directory for downloads
            delete_local_after_upload: Whether to delete local file after upload
        """
        super().__init__(
            tracker=tracker,
            extractor=extractor,
            storage=storage,
            drive_client=drive_client,
            check_interval=check_interval,
            download_temp_dir=download_temp_dir,
            output_dir=output_dir,
        )

        self.delete_local_after_upload = delete_local_after_upload
        self.output_dir = Path(output_dir) if output_dir else Path("./output")

    def process_recording(self, file_metadata: Dict) -> bool:
        """Process a recording with storage upload.

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
        local_audio_path = self.temp_dir / audio_name  # Use temp dir for processing

        # Storage path with date organization
        now = datetime.now()
        storage_path = f"audio/{now.year}/{now.month:02d}/{audio_name}"

        # Download video
        logger.info("Downloading video...")
        self.client.download_file(file_id, temp_video)

        # Extract audio
        logger.info("Extracting audio...")
        self.extractor.extract(temp_video, local_audio_path)

        # Upload to storage
        logger.info(f"Uploading to storage: {storage_path}")
        storage_result = self.storage.save(local_audio_path, storage_path)

        # Get URL for the uploaded file
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
                "audio_path": str(local_audio_path),
                "storage_path": storage_path,
                "storage_url": storage_url,
                "storage_type": type(self.storage).__name__,
                "file_size": file_metadata.get("size"),
                "size": file_metadata.get("size"),
                "mimeType": file_metadata.get("mimeType"),
                "parents": file_metadata.get("parents"),
                "modifiedTime": file_metadata.get("modifiedTime"),
                "modified_time": file_metadata.get("modifiedTime"),
                "processed_at": datetime.now().isoformat(),
            },
        )

        # Clean up local audio file if configured
        if self.delete_local_after_upload and local_audio_path.exists():
            local_audio_path.unlink()
            logger.debug("Deleted local audio file after upload")

        # Clean up temp video file
        if temp_video.exists():
            temp_video.unlink()
            logger.debug("Cleaned up temporary video file")

        logger.info(f"Successfully processed: {file_name} -> {storage_path}")
        return True

    @classmethod
    def from_config(cls, config: Dict, tracker: ProcessingTracker) -> "StorageAwareDriveMonitor":
        """Create monitor from configuration dictionary.

        Args:
            config: Configuration dictionary
            tracker: Processing tracker instance

        Returns:
            Configured StorageAwareDriveMonitor instance
        """
        # Extract configurations
        drive_config = config.get("google_drive", {})
        processing_config = config.get("processing", {})
        storage_config = config.get("storage", {})

        # Create storage adapter
        storage = StorageFactory.create(storage_config)

        # Create extractor with audio settings
        audio_config = processing_config.get("audio_format", {})
        extractor = AudioExtractor(
            bitrate=audio_config.get("bitrate", "128k"),
            sample_rate=audio_config.get("sample_rate", 44100),
            channels=audio_config.get("channels", 1),
        )

        # Create monitor
        return cls(
            tracker=tracker,
            extractor=extractor,
            storage=storage,
            output_dir=processing_config.get("output_directory", "./output"),
            check_interval=drive_config.get("check_interval_seconds", 300),
            download_temp_dir=drive_config.get("download_temp_dir"),
            delete_local_after_upload=processing_config.get("delete_local_after_upload", True),
        )
