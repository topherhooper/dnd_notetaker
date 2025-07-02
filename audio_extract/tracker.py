"""Processing tracker for keeping track of processed videos."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import threading

from .utils import get_file_hash
from .exceptions import TrackingError, InvalidAudioFileError
from .storage.db_migrations import run_migrations


class ProcessingTracker:
    """Track processed videos using SQLite database."""

    VALID_STATUSES = {"completed", "failed", "in_progress"}

    def __init__(self, db_path: Path):
        """Initialize tracker with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        # Run migrations to ensure schema is up to date
        run_migrations(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                processed_at TIMESTAMP NOT NULL,
                metadata TEXT,
                UNIQUE(file_hash)
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_hash
            ON processed_videos(file_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_processed_at
            ON processed_videos(processed_at)
        """
        )

        # Drive-specific tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drive_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                folder_id TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                modified_time TIMESTAMP,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_drive_file_id
            ON drive_files(file_id)
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                folder_id TEXT,
                files_found INTEGER,
                files_processed INTEGER,
                files_failed INTEGER,
                duration_seconds REAL
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sync_time
            ON sync_history(sync_time)
        """
        )

        conn.commit()

    def mark_processed(
        self, file_path: str, status: str = "completed", metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a video as processed.

        Args:
            file_path: Path to the video file
            status: Processing status (completed, failed, in_progress)
            metadata: Optional metadata to store with the record

        Raises:
            ValueError: If status is invalid
            TrackingError: If database operation fails
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. " f"Must be one of: {', '.join(self.VALID_STATUSES)}"
            )

        # Calculate file hash
        file_hash = self._get_file_hash_safe(file_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO processed_videos
            (file_path, file_hash, status, processed_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (file_path, file_hash, status, datetime.now(), metadata_json),
        )

        conn.commit()

    def is_processed(self, file_path: str) -> bool:
        """Check if a video has been processed.

        Args:
            file_path: Path to the video file

        Returns:
            True if processed (completed status), False otherwise
        """
        file_hash = self._get_file_hash_safe(file_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT status FROM processed_videos
            WHERE file_hash = ? AND status = 'completed'
        """,
            (file_hash,),
        )

        return cursor.fetchone() is not None

    def get_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a processed video.

        Args:
            file_path: Path to the video file

        Returns:
            Dictionary with processing info, or None if not found
        """
        file_hash = self._get_file_hash_safe(file_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT file_path, status, processed_at, metadata
            FROM processed_videos
            WHERE file_hash = ?
        """,
            (file_hash,),
        )

        row = cursor.fetchone()
        if row:
            result = {
                "file_path": row["file_path"],
                "status": row["status"],
                "processed_at": row["processed_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            }
            return result

        return None

    def get_recent_processed(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently processed videos.

        Args:
            days: Number of days to look back

        Returns:
            List of processed video records
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            SELECT file_path, status, processed_at, metadata
            FROM processed_videos
            WHERE processed_at > ?
            ORDER BY processed_at DESC
        """,
            (cutoff_date,),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "file_path": row["file_path"],
                    "status": row["status"],
                    "processed_at": row["processed_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
            )

        return results

    def get_failed_videos(self) -> List[Dict[str, Any]]:
        """Get all failed video processing attempts.

        Returns:
            List of failed video records
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT file_path, status, processed_at, metadata
            FROM processed_videos
            WHERE status = 'failed'
            ORDER BY processed_at DESC
        """
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "file_path": row["file_path"],
                    "status": row["status"],
                    "processed_at": row["processed_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
            )

        return results

    def mark_for_reprocessing(self, file_path: str) -> None:
        """Remove a video from processed records to allow reprocessing.

        Args:
            file_path: Path to the video file
        """
        file_hash = self._get_file_hash_safe(file_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM processed_videos
            WHERE file_hash = ?
        """,
            (file_hash,),
        )

        conn.commit()

    def cleanup_old_entries(self, days: int = 90) -> int:
        """Remove old entries from the database.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of deleted entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            DELETE FROM processed_videos
            WHERE processed_at < ?
        """,
            (cutoff_date,),
        )

        deleted = cursor.rowcount
        conn.commit()

        return deleted

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary with statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM processed_videos
        """
        )

        row = cursor.fetchone()

        total = row["total"] or 0
        completed = row["completed"] or 0
        failed = row["failed"] or 0

        success_rate = (completed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(success_rate, 2),
        }

    def close(self):
        """Close database connection."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")

    def _get_file_hash_safe(self, file_path: str) -> str:
        """Get file hash, using path as fallback if file doesn't exist.

        Args:
            file_path: Path to file

        Returns:
            File hash or path-based hash
        """
        path = Path(file_path)
        if path.exists():
            return get_file_hash(path)
        else:
            # Use path as hash for non-existent files
            import hashlib

            return hashlib.sha256(str(file_path).encode()).hexdigest()

    # Drive-specific methods
    def mark_drive_file_processed(
        self, file_id: str, status: str = "completed", metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a Drive file as processed.

        Args:
            file_id: Google Drive file ID
            status: Processing status
            metadata: Processing metadata including storage info
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. " f"Must be one of: {', '.join(self.VALID_STATUSES)}"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        # First ensure the file is recorded in drive_files
        if metadata:
            self.record_drive_file(metadata)

        # Then mark it as processed in processed_videos using file_id as identifier
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO processed_videos
            (file_path, file_hash, status, processed_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                f"drive://{file_id}",  # Use drive:// prefix for Drive files
                file_id,  # Use file_id as hash for Drive files
                status,
                datetime.now(),
                metadata_json,
            ),
        )

        conn.commit()

    def is_drive_file_processed(self, file_id: str) -> bool:
        """Check if a Drive file has been processed.

        Args:
            file_id: Google Drive file ID

        Returns:
            True if processed (completed status), False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT status FROM processed_videos
            WHERE file_hash = ? AND status = 'completed'
        """,
            (file_id,),
        )

        return cursor.fetchone() is not None

    def get_drive_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a processed Drive file.

        Args:
            file_id: Google Drive file ID

        Returns:
            Dictionary with processing info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT file_path, status, processed_at, metadata
            FROM processed_videos
            WHERE file_hash = ?
        """,
            (file_id,),
        )

        row = cursor.fetchone()
        if row:
            result = {
                "file_path": row["file_path"],
                "status": row["status"],
                "processed_at": row["processed_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            }
            return result

        return None

    def record_drive_file(self, file_metadata: Dict[str, Any]) -> None:
        """Record a Drive file discovery.

        Args:
            file_metadata: Google Drive file metadata
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if we have storage metadata in the file_metadata
        storage_path = file_metadata.get("storage_path")
        storage_url = file_metadata.get("storage_url")
        storage_type = file_metadata.get("storage_type")
        processed_at = file_metadata.get("processed_at")
        upload_timestamp = (
            datetime.fromisoformat(processed_at)
            if processed_at
            else None
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO drive_files
            (file_id, file_name, folder_id, mime_type, size_bytes, modified_time,
             storage_path, storage_url, storage_type, upload_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                file_metadata.get("id"),
                file_metadata.get("name"),
                file_metadata.get("parents", [None])[0],
                file_metadata.get("mimeType"),
                int(file_metadata.get("size", 0)),
                (
                    datetime.fromisoformat(
                        file_metadata.get("modifiedTime", "").replace("Z", "+00:00")
                    )
                    if file_metadata.get("modifiedTime")
                    else None
                ),
                storage_path,
                storage_url,
                storage_type,
                upload_timestamp,
            ),
        )

        conn.commit()

    def record_sync(
        self,
        folder_id: str,
        files_found: int,
        files_processed: int,
        files_failed: int,
        duration_seconds: float,
    ) -> None:
        """Record a sync operation.

        Args:
            folder_id: Google Drive folder ID
            files_found: Number of files found
            files_processed: Number successfully processed
            files_failed: Number that failed
            duration_seconds: Duration of sync operation
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO sync_history
            (folder_id, files_found, files_processed, files_failed, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """,
            (folder_id, files_found, files_processed, files_failed, duration_seconds),
        )

        conn.commit()

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of sync history entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM sync_history
            ORDER BY sync_time DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "sync_time": row["sync_time"],
                    "folder_id": row["folder_id"],
                    "files_found": row["files_found"],
                    "files_processed": row["files_processed"],
                    "files_failed": row["files_failed"],
                    "duration_seconds": row["duration_seconds"],
                }
            )

        return results
