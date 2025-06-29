"""Google Drive monitoring for new Meet recordings."""

import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable

from .tracker import ProcessingTracker
from .extractor import AudioExtractor
from .exceptions import AudioExtractionError


logger = logging.getLogger(__name__)


class DriveMonitor:
    """Monitor Google Drive for new Meet recordings and process them."""
    
    def __init__(
        self,
        drive_handler,
        tracker: ProcessingTracker,
        extractor: AudioExtractor,
        output_dir: Path,
        check_interval: int = 300  # 5 minutes
    ):
        """Initialize Drive monitor.
        
        Args:
            drive_handler: Google Drive handler instance
            tracker: Processing tracker instance
            extractor: Audio extractor instance
            output_dir: Directory to save extracted audio
            check_interval: Seconds between checks (default: 5 minutes)
        """
        self.drive_handler = drive_handler
        self.tracker = tracker
        self.extractor = extractor
        self.output_dir = Path(output_dir)
        self.check_interval = check_interval
        self.running = False
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def find_meet_recordings(self, folder_id: str, days_back: int = 7) -> List[Dict]:
        """Find Meet recordings in Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID to search
            days_back: How many days back to search
        
        Returns:
            List of file metadata dictionaries
        """
        # Calculate date threshold
        date_threshold = datetime.now() - timedelta(days=days_back)
        
        # Search for video files in the folder
        query = f"'{folder_id}' in parents and (mimeType='video/mp4' or mimeType='video/webm')"
        
        try:
            files = self.drive_handler.search_files(query)
            
            # Filter for recent files
            recent_files = []
            for file in files:
                # Parse modified time
                modified_time = datetime.fromisoformat(
                    file.get('modifiedTime', '').replace('Z', '+00:00')
                )
                
                if modified_time > date_threshold:
                    recent_files.append(file)
            
            logger.info(f"Found {len(recent_files)} recent Meet recordings")
            return recent_files
            
        except Exception as e:
            logger.error(f"Error searching Drive: {e}")
            return []
    
    def process_recording(self, file_metadata: Dict) -> bool:
        """Process a single Meet recording.
        
        Args:
            file_metadata: Google Drive file metadata
        
        Returns:
            True if successful, False otherwise
        """
        file_id = file_metadata['id']
        file_name = file_metadata['name']
        
        # Check if already processed
        if self.tracker.is_processed(file_id):
            logger.info(f"Already processed: {file_name}")
            return True
        
        logger.info(f"Processing new recording: {file_name}")
        
        try:
            # Download video to temporary location
            temp_video = self.output_dir / f"temp_{file_id}.mp4"
            
            logger.info(f"Downloading: {file_name}")
            self.drive_handler.download_file(file_id, str(temp_video))
            
            # Extract audio
            audio_name = Path(file_name).stem + "_audio.mp3"
            audio_path = self.output_dir / audio_name
            
            logger.info(f"Extracting audio to: {audio_path}")
            self.extractor.extract(temp_video, audio_path)
            
            # Upload audio back to Drive (optional)
            if hasattr(self.drive_handler, 'upload_file'):
                logger.info("Uploading audio to Drive")
                audio_file_id = self.drive_handler.upload_file(
                    str(audio_path),
                    file_metadata.get('parents', [None])[0]
                )
            
            # Mark as processed
            self.tracker.mark_processed(
                file_id,
                status='completed',
                metadata={
                    'file_name': file_name,
                    'audio_path': str(audio_path),
                    'processed_at': datetime.now().isoformat()
                }
            )
            
            # Clean up temporary video
            if temp_video.exists():
                temp_video.unlink()
            
            logger.info(f"Successfully processed: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}")
            
            # Mark as failed
            self.tracker.mark_processed(
                file_id,
                status='failed',
                metadata={
                    'file_name': file_name,
                    'error': str(e)
                }
            )
            
            # Clean up on failure
            if 'temp_video' in locals() and temp_video.exists():
                temp_video.unlink()
            
            return False
    
    def monitor_once(self, folder_id: str) -> Dict[str, int]:
        """Run one monitoring cycle.
        
        Args:
            folder_id: Google Drive folder ID to monitor
        
        Returns:
            Dictionary with processing statistics
        """
        logger.info("Starting monitoring cycle")
        
        # Find new recordings
        recordings = self.find_meet_recordings(folder_id)
        
        # Process each recording
        processed = 0
        failed = 0
        skipped = 0
        
        for recording in recordings:
            if self.tracker.is_processed(recording['id']):
                skipped += 1
            elif self.process_recording(recording):
                processed += 1
            else:
                failed += 1
        
        stats = {
            'found': len(recordings),
            'processed': processed,
            'failed': failed,
            'skipped': skipped
        }
        
        logger.info(f"Monitoring cycle complete: {stats}")
        return stats
    
    def monitor_continuous(
        self,
        folder_id: str,
        callback: Optional[Callable[[Dict], None]] = None
    ):
        """Monitor continuously until stopped.
        
        Args:
            folder_id: Google Drive folder ID to monitor
            callback: Optional callback for each cycle's statistics
        """
        logger.info(f"Starting continuous monitoring of folder: {folder_id}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        self.running = True
        
        while self.running:
            try:
                # Run one monitoring cycle
                stats = self.monitor_once(folder_id)
                
                # Call callback if provided
                if callback:
                    callback(stats)
                
                # Wait for next cycle
                if self.running:
                    logger.info(f"Waiting {self.check_interval} seconds until next check...")
                    time.sleep(self.check_interval)
                    
            except KeyboardInterrupt:
                logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                # Continue monitoring after error
                if self.running:
                    time.sleep(self.check_interval)
        
        logger.info("Monitoring stopped")
    
    def stop(self):
        """Stop continuous monitoring."""
        self.running = False