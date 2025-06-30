"""Minimal Google Drive client for audio_extract needs."""

import io
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from .auth import DriveAuth

logger = logging.getLogger(__name__)


class DriveClient:
    """Minimal Google Drive client focused on Meet recording operations."""

    def __init__(self, auth: Optional[DriveAuth] = None):
        """Initialize Drive client.

        Args:
            auth: DriveAuth instance. If not provided, creates a new one.
        """
        self.auth = auth or DriveAuth()
        self._service = None

    @property
    def service(self):
        """Get or create Drive API service.

        Returns:
            googleapiclient.discovery.Resource: Drive API service
        """
        if not self._service:
            credentials = self.auth.get_credentials()
            self._service = build("drive", "v3", credentials=credentials)
            logger.info("Drive API service initialized")
        return self._service

    def list_files(
        self, folder_id: Optional[str] = None, query: Optional[str] = None, page_size: int = 100
    ) -> List[Dict]:
        """List files in Drive.

        Args:
            folder_id: Folder ID to list files from
            query: Custom query string (overrides folder_id)
            page_size: Number of results per page

        Returns:
            List of file metadata dictionaries
        """
        # Build query
        if query is None and folder_id:
            query = f"'{folder_id}' in parents and trashed = false"
        elif query is None:
            query = "trashed = false"

        results = []
        page_token = None

        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, createdTime)",
                    pageToken=page_token,
                )
                .execute()
            )

            files = response.get("files", [])
            results.extend(files)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info(f"Found {len(results)} files")
        return results

    def find_meet_recordings(self, folder_id: str, days_back: Optional[int] = None) -> List[Dict]:
        """Find Google Meet recordings in a folder.

        Args:
            folder_id: Drive folder ID to search
            days_back: Only include files modified within this many days

        Returns:
            List of Meet recording file metadata
        """
        # Build query for video files
        query_parts = [
            f"'{folder_id}' in parents",
            "trashed = false",
            "(mimeType = 'video/mp4' or mimeType = 'video/webm' or mimeType = 'video/x-matroska')",
        ]

        # Add time filter if specified
        if days_back:
            cutoff_date = datetime.now().isoformat() + "Z"
            # Note: Drive API doesn't support relative date queries,
            # so we'll filter in Python

        query = " and ".join(query_parts)

        # Get all video files
        files = self.list_files(query=query)

        # Filter for Meet recordings (by name pattern and date)
        meet_recordings = []
        for file in files:
            # Common Meet recording name patterns
            name_lower = file["name"].lower()
            if any(pattern in name_lower for pattern in ["meet", "recording", "video"]):
                # Check date if needed
                if days_back:
                    modified = datetime.fromisoformat(file["modifiedTime"].replace("Z", "+00:00"))
                    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
                    if modified < cutoff:
                        continue

                meet_recordings.append(file)

        logger.info(f"Found {len(meet_recordings)} Meet recordings")
        return meet_recordings

    def download_file(
        self,
        file_id: str,
        output_path: Union[str, Path],
        chunk_size: int = 32 * 1024 * 1024,  # 32MB chunks
    ) -> Path:
        """Download a file from Drive.

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save the file
            chunk_size: Download chunk size in bytes

        Returns:
            Path to the downloaded file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get file metadata first
        file_metadata = self.service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get("name", "download")
        file_size = int(file_metadata.get("size", 0))

        logger.info(f"Downloading '{file_name}' ({file_size:,} bytes)")

        # Download file
        request = self.service.files().get_media(fileId=file_id)

        with open(output_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=chunk_size)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Download progress: {progress}%")

        logger.info(f"Downloaded to: {output_path}")
        return output_path

    def get_file_info(self, file_id: str) -> Dict:
        """Get detailed file information.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dictionary
        """
        file_info = (
            self.service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, createdTime, parents, md5Checksum",
            )
            .execute()
        )

        return file_info

    def test_connection(self) -> bool:
        """Test Drive API connection.

        Returns:
            bool: True if connection is working
        """
        # Try to get the root folder
        about = self.service.about().get(fields="user").execute()
        user = about.get("user", {})
        logger.info(f"Connected as: {user.get('emailAddress', 'Unknown')}")
        return True
