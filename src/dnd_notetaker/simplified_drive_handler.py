"""Simplified Google Drive handler for downloading recordings"""

import logging
from pathlib import Path
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class SimplifiedDriveHandler:
    """Download Google Meet recordings from Drive"""
    
    def __init__(self, service_account_path: Path, config=None):
        """Initialize with service account credentials"""
        self.config = config
        
        if not config or not config.dry_run:
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_path),
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.service = build('drive', 'v3', credentials=credentials)
        else:
            self.service = None
    
    def download_file(self, file_id: str, output_dir: Path) -> Path:
        """Download a specific file by ID
        
        Args:
            file_id: Google Drive file ID
            output_dir: Directory to save the file
            
        Returns:
            Path to downloaded file
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            output_path = output_dir / "meeting.mp4"
            print(f"[DRY RUN] Would download from Google Drive:")
            print(f"  File ID: {file_id}")
            print(f"  Destination: {output_path}")
            return output_path
            
        try:
            if not self.service:
                raise RuntimeError("Drive service not initialized (check dry_run mode)")
                
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='name,size,mimeType'
            ).execute()
            
            filename = file_metadata['name']
            file_size = int(file_metadata.get('size', 0))
            
            # Ensure it's a video file
            mime_type = file_metadata.get('mimeType', '')
            if not mime_type.startswith('video/'):
                raise ValueError(f"File is not a video: {mime_type}")
            
            # Sanitize filename for filesystem
            safe_filename = self._sanitize_filename(filename)
            
            # Download file
            output_path = output_dir / safe_filename
            logger.info(f"Downloading: {filename} ({self._format_size(file_size)})")
            
            if not self.service:
                raise RuntimeError("Drive service not initialized")
                
            request = self.service.files().get_media(fileId=file_id)
            
            # Stream directly to file instead of memory
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=50*1024*1024)  # 50MB chunks
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Download progress: {int(status.progress() * 100)}%")
            
            logger.info(f"✓ Downloaded to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise RuntimeError(f"Download failed: {e}")
    
    def download_most_recent(self, output_dir: Path) -> Path:
        """Download the most recent Meet recording
        
        Args:
            output_dir: Directory to save the file
            
        Returns:
            Path to downloaded file
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            output_path = output_dir / "meeting.mp4"
            print(f"[DRY RUN] Would search for most recent Google Meet recording")
            print(f"[DRY RUN] Would download most recent file to: {output_path}")
            return output_path
            
        try:
            # Search for recent video files
            # Look for files with "Meet" in name or video mime type
            query = "(name contains 'Meet' or mimeType contains 'video/') and trashed = false"
            
            if not self.service:
                raise RuntimeError("Drive service not initialized (check dry_run mode)")
                
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, modifiedTime, size, mimeType)',
                orderBy='modifiedTime desc',
                pageSize=10
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                raise ValueError("No Meet recordings found in Drive")
            
            # Find first video file
            video_file = None
            for file in files:
                if file.get('mimeType', '').startswith('video/'):
                    video_file = file
                    break
            
            if not video_file:
                # Fallback: assume first file is video
                video_file = files[0]
            
            logger.info(f"Found recording: {video_file['name']}")
            logger.info(f"Modified: {video_file['modifiedTime']}")
            
            # Download the file
            return self.download_file(video_file['id'], output_dir)
            
        except Exception as e:
            logger.error(f"Failed to find recent recording: {e}")
            raise RuntimeError(f"Failed to find recent recording: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for all operating systems"""
        # Replace slashes with dashes
        filename = filename.replace("/", "-").replace("\\", "-")
        # Replace colons with dashes
        filename = filename.replace(":", "-")
        # Replace any other potentially problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "-")
        return filename
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"