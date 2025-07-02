"""Local file system storage adapter."""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from .base import StorageAdapter, StorageError


logger = logging.getLogger(__name__)


class LocalStorageAdapter(StorageAdapter):
    """Storage adapter for local file system."""

    def __init__(self, base_path: str = "./output"):
        """Initialize local storage adapter.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local storage at: {self.base_path.absolute()}")

    def save(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Save a file to local storage.

        Args:
            local_path: Path to local file to copy
            remote_path: Relative path in storage

        Returns:
            Dictionary with file metadata
        """
        # Ensure local_path exists
        if not local_path.exists():
            raise StorageError(f"Source file not found: {local_path}")

        # Create full destination path
        dest_path = self.base_path / remote_path

        # Create parent directories if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(local_path, dest_path)

        # Get file stats
        stats = dest_path.stat()

        result = {
            "path": str(dest_path),
            "url": f"file://{dest_path.absolute()}",
            "size": stats.st_size,
            "upload_time": datetime.now().isoformat(),
        }

        logger.debug(f"Saved file to local storage: {dest_path}")
        return result

    def exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage."""
        full_path = self.base_path / remote_path
        return full_path.exists() and full_path.is_file()

    def get_url(self, remote_path: str, expiration_hours: Optional[int] = None) -> str:
        """Get file URL (local file:// URL)."""
        full_path = self.base_path / remote_path

        if not full_path.exists():
            raise StorageError(f"File not found: {remote_path}")

        return f"file://{full_path.absolute()}"

    def delete(self, remote_path: str) -> None:
        """Delete file from local storage."""
        full_path = self.base_path / remote_path

        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            logger.debug(f"Deleted file: {full_path}")

    def list_files(self, prefix: str = "") -> List[str]:
        """List files with given prefix."""
        prefix_path = self.base_path / prefix

        if not prefix_path.exists():
            return []

        files = []

        # Walk directory tree
        for path in prefix_path.rglob("*"):
            if path.is_file():
                # Get relative path from base
                relative_path = path.relative_to(self.base_path)
                files.append(str(relative_path))

        return sorted(files)
