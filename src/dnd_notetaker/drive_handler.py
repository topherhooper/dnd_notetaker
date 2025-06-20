import argparse
import io
import json
import logging
import os

from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

from .auth_service_account import GoogleAuthenticator


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
LOGGER = logging.getLogger(__file__)


class DriveHandler:
    def __init__(self):
        self.drive_service = None
        
        # Default folder ID for recordings
        self.default_folder_id = "14EVI64FlpZCwRy4UL4ZhGjlsjK55XL1h"

        # Initialize Drive service at startup
        self.setup_drive_service()

        LOGGER.debug("DriveHandler initialized with Drive service")

    def setup_drive_service(self):
        """Set up Google Drive API service using service account authentication"""
        auth = GoogleAuthenticator()
        self.drive_service, _ = auth.get_services()

    def sanitize_filename(self, filename):
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

    def list_recordings(self, folder_id=None):
        """List all video recordings from a specific Google Drive folder"""
        if folder_id is None:
            folder_id = self.default_folder_id
            
        recordings = []
        
        try:
            if not self.drive_service:
                self.setup_drive_service()
                
            # Query for all video files in the folder
            query = f"'{folder_id}' in parents and mimeType contains 'video/'"
            
            if not self.drive_service:
                raise RuntimeError("Drive service not initialized")
                
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, size, mimeType, createdTime, modifiedTime)",
                orderBy="createdTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            for idx, file in enumerate(files):
                recordings.append({
                    "index": idx + 1,
                    "file_name": file.get("name", "Unknown"),
                    "file_size_mb": int(file.get("size", 0)) / (1024 * 1024),
                    "file_id": file.get("id"),
                    "mime_type": file.get("mimeType", ""),
                    "created_time": file.get("createdTime", ""),
                    "modified_time": file.get("modifiedTime", ""),
                })
                
            LOGGER.info(f"Found {len(recordings)} recordings in Drive folder")
            return recordings
            
        except Exception as e:
            LOGGER.error(f"Error listing Drive folder recordings: {str(e)}")
            raise

    def download_file(self, file_id, download_dir):
        """Download a file from Google Drive by its ID"""
        if not self.drive_service:
            self.setup_drive_service()

        try:
            if not self.drive_service:
                raise RuntimeError("Drive service not initialized")
                
            # Get file metadata with additional fields
            file_metadata = (
                self.drive_service.files()
                .get(fileId=file_id, fields="name,size,mimeType")
                .execute()
            )
            original_name = file_metadata["name"]
            mime_type = file_metadata.get("mimeType", "")
            file_size = int(file_metadata.get("size", 0))

            # Add extension if missing based on MIME type
            if not os.path.splitext(original_name)[1] and mime_type:
                mime_extensions = {
                    "video/mp4": ".mp4",
                    "video/webm": ".webm",
                    "video/quicktime": ".mov",
                    "video/x-msvideo": ".avi",
                    "video/x-matroska": ".mkv",
                }
                ext = mime_extensions.get(mime_type, "")
                if ext:
                    original_name += ext

            safe_filename = self.sanitize_filename(original_name)

            LOGGER.info(f"Found Drive file: {original_name}")
            LOGGER.info(f"MIME type: {mime_type}")
            LOGGER.info(f"File size: {file_size / (1024*1024):.2f} MB")

            # Check if file already exists
            filepath = os.path.join(download_dir, safe_filename)
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if existing_size == file_size:
                    LOGGER.info("=" * 60)
                    LOGGER.info("SKIPPING DOWNLOAD - File already exists")
                    LOGGER.info(f"File: {filepath}")
                    LOGGER.info(f"Size: {file_size / (1024*1024):.2f} MB")
                    LOGGER.info("=" * 60)
                    return filepath
                else:
                    LOGGER.warning(f"File exists but size differs.")
                    LOGGER.warning(
                        f"Expected: {file_size} bytes, Found: {existing_size} bytes"
                    )
                    LOGGER.info("Redownloading...")
            else:
                LOGGER.info("File doesn't exist. Starting download...")

            # Ensure directory exists
            os.makedirs(download_dir, exist_ok=True)

            # Download file directly to disk
            if not self.drive_service:
                raise RuntimeError("Drive service not initialized")
                
            request = self.drive_service.files().get_media(fileId=file_id)

            # Open file for writing
            with open(filepath, "wb") as f:
                downloader = MediaIoBaseDownload(
                    f, request, chunksize=50 * 1024 * 1024
                )  # 50MB chunks
                done = False

                with tqdm(total=100, desc=f"Downloading {safe_filename}") as pbar:
                    last_progress = 0
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            pbar.update(progress - last_progress)
                            last_progress = progress

            LOGGER.info(f"Download complete: {filepath}")

            # Log successful download
            final_size = os.path.getsize(filepath)
            LOGGER.info("=" * 60)
            LOGGER.info("DOWNLOAD COMPLETED SUCCESSFULLY")
            LOGGER.info(f"File: {filepath}")
            LOGGER.info(f"Size: {final_size / (1024*1024):.2f} MB")
            LOGGER.info("=" * 60)

            return filepath

        except Exception as e:
            LOGGER.error(f"Error downloading from Drive: {str(e)}")
            raise

    def check_existing_downloads(self, name_filter, download_dir):
        """Check if we already have a downloaded file matching the name filter"""
        if not os.path.exists(download_dir):
            return None

        # Look for video files that might be meeting recordings
        video_extensions = [".mp4", ".webm", ".mov", ".avi", ".mkv"]

        for filename in os.listdir(download_dir):
            # Check if it's a video file
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                # Check if filename contains relevant keywords
                if any(
                    keyword in filename
                    for keyword in ["DnD", "D&D", "Recording", name_filter]
                ):
                    filepath = os.path.join(download_dir, filename)
                    file_size = os.path.getsize(filepath)
                    LOGGER.info(
                        f"Found existing file: {filename} ({file_size / (1024*1024):.2f} MB)"
                    )
                    return filepath
        return None

    def find_recording_by_name(self, name_filter, folder_id=None):
        """Find a recording in Drive folder that matches the name filter"""
        recordings = self.list_recordings(folder_id)
        
        # Try to find exact match first
        for recording in recordings:
            if name_filter.lower() in recording["file_name"].lower():
                LOGGER.info(f"Found matching recording: {recording['file_name']}")
                return recording
        
        # If no match found, return None
        LOGGER.warning(f"No recording found matching: {name_filter}")
        return None

    def download_recording(self, name_filter, download_dir, folder_id=None):
        """Download a recording that matches the name filter"""
        try:
            # First check if we already have the file
            existing_file = self.check_existing_downloads(name_filter, download_dir)
            if existing_file:
                LOGGER.info("=" * 60)
                LOGGER.info("USING EXISTING DOWNLOAD")
                LOGGER.info(f"File: {existing_file}")
                LOGGER.info("Skipping Drive search and download")
                LOGGER.info("=" * 60)
                return existing_file

            # Find recording in Drive
            recording = self.find_recording_by_name(name_filter, folder_id)
            if not recording:
                raise Exception(f"No recording found matching: {name_filter}")
                
            # Download the file
            return self.download_file(recording["file_id"], download_dir)

        except Exception as e:
            LOGGER.error(f"Error in download_recording: {str(e)}")
            raise


