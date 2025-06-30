"""Google Cloud Storage adapter."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

try:
    from google.cloud import storage

    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    storage = None

from .base import StorageAdapter, StorageError


logger = logging.getLogger(__name__)


class GCSStorageAdapter(StorageAdapter):
    """Storage adapter for Google Cloud Storage."""

    def __init__(
        self,
        bucket_name: str,
        credentials_path: str,
        public_access: bool = True,
        url_expiration_hours: int = 24,
    ):
        """Initialize GCS storage adapter.

        Args:
            bucket_name: Name of GCS bucket
            credentials_path: Path to service account JSON
            public_access: Whether to use public URLs (vs signed)
            url_expiration_hours: Hours until signed URLs expire

        Raises:
            StorageError: If GCS libraries not installed
        """
        if not HAS_GCS:
            raise StorageError(
                "Google Cloud Storage libraries not installed. "
                "Install with: pip install google-cloud-storage"
            )

        self.bucket_name = bucket_name
        self.public_access = public_access
        self.url_expiration_hours = url_expiration_hours

        # Initialize client with service account
        self.client = storage.Client.from_service_account_json(credentials_path)
        self.bucket = self.client.bucket(bucket_name)

        # Test bucket access
        if not self.bucket.exists():
            raise StorageError(f"Bucket '{bucket_name}' not found or not accessible")

        logger.info(f"Initialized GCS storage for bucket: {bucket_name}")

    def save(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Save a file to GCS.

        Args:
            local_path: Path to local file to upload
            remote_path: Path in GCS bucket

        Returns:
            Dictionary with file metadata
        """
        if not local_path.exists():
            raise StorageError(f"Source file not found: {local_path}")

        # Create blob
        blob = self.bucket.blob(remote_path)

        # Upload file
        blob.upload_from_filename(str(local_path))

        # Get file stats
        stats = local_path.stat()

        result = {
            "path": remote_path,
            "url": self._get_blob_url(blob),
            "size": stats.st_size,
            "upload_time": datetime.now().isoformat(),
            "bucket": self.bucket_name,
        }

        logger.debug(f"Uploaded file to GCS: gs://{self.bucket_name}/{remote_path}")
        return result

    def exists(self, remote_path: str) -> bool:
        """Check if blob exists in GCS."""
        blob = self.bucket.blob(remote_path)
        return blob.exists()

    def get_url(self, remote_path: str, expiration_hours: Optional[int] = None) -> str:
        """Get URL to access file in GCS."""
        blob = self.bucket.blob(remote_path)

        if not blob.exists():
            raise StorageError(f"File not found in GCS: {remote_path}")

        return self._get_blob_url(blob, expiration_hours)

    def delete(self, remote_path: str) -> None:
        """Delete blob from GCS."""
        blob = self.bucket.blob(remote_path)
        blob.delete()
        logger.debug(f"Deleted blob: gs://{self.bucket_name}/{remote_path}")

    def list_files(self, prefix: str = "") -> List[str]:
        """List blobs with given prefix."""
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        return [blob.name for blob in blobs]

    def _get_blob_url(self, blob, expiration_hours: Optional[int] = None) -> str:
        """Get URL for a blob (public or signed)."""
        if self.public_access:
            return blob.public_url
        else:
            # Use provided expiration or default
            hours = expiration_hours or self.url_expiration_hours
            expiration = timedelta(hours=hours)
            return blob.generate_signed_url(expiration)
