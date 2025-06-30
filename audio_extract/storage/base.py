"""Base storage adapter interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    @abstractmethod
    def save(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Save a file to storage.

        Args:
            local_path: Path to local file to upload
            remote_path: Path in storage (e.g., "audio/2025/01/file.mp3")

        Returns:
            Dictionary with metadata about saved file:
                - path: Storage path
                - url: URL to access file
                - size: File size in bytes
                - upload_time: Upload timestamp

        Raises:
            StorageError: If save operation fails
        """
        pass

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            remote_path: Path in storage

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_url(self, remote_path: str, expiration_hours: Optional[int] = None) -> str:
        """Get URL to access a file.

        Args:
            remote_path: Path in storage
            expiration_hours: Hours until URL expires (for signed URLs)

        Returns:
            URL to access the file

        Raises:
            StorageError: If file doesn't exist
        """
        pass

    @abstractmethod
    def delete(self, remote_path: str) -> None:
        """Delete a file from storage.

        Args:
            remote_path: Path in storage

        Note:
            Should not raise error if file doesn't exist
        """
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files with given prefix.

        Args:
            prefix: Path prefix to filter by (e.g., "audio/2025/01/")

        Returns:
            List of file paths matching the prefix
        """
        pass
