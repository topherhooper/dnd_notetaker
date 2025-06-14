import argparse
import io
import json
import logging
import os

from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

from .auth_service_account import GoogleAuthenticator


def setup_logging(name):
    """Configure logging with timestamps and appropriate formatting"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(name)


class DriveHandler:
    def __init__(self):
        self.logger = setup_logging("DriveHandler")
        self.drive_service = None
        
        # Default folder ID for recordings
        self.default_folder_id = "14EVI64FlpZCwRy4UL4ZhGjlsjK55XL1h"

        # Initialize Drive service at startup
        self.setup_drive_service()

        self.logger.debug("DriveHandler initialized with Drive service")

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
                
            self.logger.info(f"Found {len(recordings)} recordings in Drive folder")
            return recordings
            
        except Exception as e:
            self.logger.error(f"Error listing Drive folder recordings: {str(e)}")
            raise

    def download_file(self, file_id, download_dir):
        """Download a file from Google Drive by its ID"""
        if not self.drive_service:
            self.setup_drive_service()

        try:
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

            self.logger.info(f"Found Drive file: {original_name}")
            self.logger.info(f"MIME type: {mime_type}")
            self.logger.info(f"File size: {file_size / (1024*1024):.2f} MB")

            # Check if file already exists
            filepath = os.path.join(download_dir, safe_filename)
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if existing_size == file_size:
                    self.logger.info("=" * 60)
                    self.logger.info("SKIPPING DOWNLOAD - File already exists")
                    self.logger.info(f"File: {filepath}")
                    self.logger.info(f"Size: {file_size / (1024*1024):.2f} MB")
                    self.logger.info("=" * 60)
                    return filepath
                else:
                    self.logger.warning(f"File exists but size differs.")
                    self.logger.warning(
                        f"Expected: {file_size} bytes, Found: {existing_size} bytes"
                    )
                    self.logger.info("Redownloading...")
            else:
                self.logger.info("File doesn't exist. Starting download...")

            # Ensure directory exists
            os.makedirs(download_dir, exist_ok=True)

            # Download file directly to disk
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

            self.logger.info(f"Download complete: {filepath}")

            # Log successful download
            final_size = os.path.getsize(filepath)
            self.logger.info("=" * 60)
            self.logger.info("DOWNLOAD COMPLETED SUCCESSFULLY")
            self.logger.info(f"File: {filepath}")
            self.logger.info(f"Size: {final_size / (1024*1024):.2f} MB")
            self.logger.info("=" * 60)

            return filepath

        except Exception as e:
            self.logger.error(f"Error downloading from Drive: {str(e)}")
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
                    self.logger.info(
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
                self.logger.info(f"Found matching recording: {recording['file_name']}")
                return recording
        
        # If no match found, return None
        self.logger.warning(f"No recording found matching: {name_filter}")
        return None

    def download_recording(self, name_filter, download_dir, folder_id=None):
        """Download a recording that matches the name filter"""
        try:
            # First check if we already have the file
            existing_file = self.check_existing_downloads(name_filter, download_dir)
            if existing_file:
                self.logger.info("=" * 60)
                self.logger.info("USING EXISTING DOWNLOAD")
                self.logger.info(f"File: {existing_file}")
                self.logger.info("Skipping Drive search and download")
                self.logger.info("=" * 60)
                return existing_file

            # Find recording in Drive
            recording = self.find_recording_by_name(name_filter, folder_id)
            if not recording:
                raise Exception(f"No recording found matching: {name_filter}")
                
            # Download the file
            return self.download_file(recording["file_id"], download_dir)

        except Exception as e:
            self.logger.error(f"Error in download_recording: {str(e)}")
            raise


def main():
    """Main function for testing drive handler independently"""
    logger = setup_logging("DriveHandlerMain")

    parser = argparse.ArgumentParser(
        description="Download recordings from Google Drive"
    )
    parser.add_argument("--output", "-o", help="Output directory", default="output")
    parser.add_argument(
        "--folder", "-f", help="Google Drive folder ID", default=None
    )
    parser.add_argument(
        "--list", action="store_true", help="List available recordings"
    )
    parser.add_argument(
        "--name", "-n", help="Name filter for finding recordings"
    )
    parser.add_argument(
        "--id", "-i", help="File ID to download directly"
    )
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    logger.debug(f"Ensuring output directory exists: {args.output}")

    # Create handler
    handler = DriveHandler()

    try:
        if args.list:
            # List recordings
            logger.info("Listing recordings in Drive folder...")
            recordings = handler.list_recordings(args.folder)
            
            print("\nAvailable Recordings:")
            print("-" * 80)
            for rec in recordings:
                print(f"{rec['index']:2d}. {rec['file_name']}")
                print(f"    Size: {rec['file_size_mb']:.1f} MB")
                print(f"    Created: {rec['created_time'][:10]}")
                print()
                
        elif args.id:
            # Download by file ID
            logger.info(f"Downloading file by ID: {args.id}")
            filepath = handler.download_file(args.id, args.output)
            logger.info(f"Successfully downloaded to: {filepath}")
            
        elif args.name:
            # Download by name filter
            logger.info(f"Searching for recording matching: {args.name}")
            filepath = handler.download_recording(args.name, args.output, args.folder)
            logger.info(f"Successfully downloaded to: {filepath}")
            
        else:
            # Default: list recordings
            logger.info("No action specified. Listing recordings...")
            recordings = handler.list_recordings(args.folder)
            
            print("\nAvailable Recordings:")
            print("-" * 80)
            for rec in recordings:
                print(f"{rec['index']:2d}. {rec['file_name']}")
                print(f"    Size: {rec['file_size_mb']:.1f} MB")
                print(f"    Created: {rec['created_time'][:10]}")
                print()

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()