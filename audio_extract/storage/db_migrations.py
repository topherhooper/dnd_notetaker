"""Database migrations for storage enhancements."""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple, Callable

logger = logging.getLogger(__name__)


def get_db_version(conn: sqlite3.Connection) -> int:
    """Get current database version."""
    cursor = conn.cursor()

    # Create version table if not exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Get current version
    cursor.execute("SELECT MAX(version) FROM db_version")
    result = cursor.fetchone()
    return result[0] if result[0] is not None else 0


def set_db_version(conn: sqlite3.Connection, version: int):
    """Set database version."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO db_version (version) VALUES (?)", (version,))
    conn.commit()


def migration_v1_add_storage_fields(conn: sqlite3.Connection):
    """Add storage-related fields to drive_files table."""
    cursor = conn.cursor()

    # Add new columns to drive_files table
    try:
        cursor.execute("ALTER TABLE drive_files ADD COLUMN storage_path TEXT")
        cursor.execute("ALTER TABLE drive_files ADD COLUMN storage_url TEXT")
        cursor.execute("ALTER TABLE drive_files ADD COLUMN storage_type TEXT")
        cursor.execute("ALTER TABLE drive_files ADD COLUMN upload_timestamp TIMESTAMP")
        logger.info("Added storage fields to drive_files table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.debug("Storage columns already exist")
        else:
            raise

    # Create index for storage queries
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_storage_path
        ON drive_files(storage_path)
    """
    )

    conn.commit()


def migration_v2_add_processing_metadata(conn: sqlite3.Connection):
    """Add enhanced metadata fields for processing."""
    cursor = conn.cursor()

    # Add new columns to processed_videos table
    try:
        cursor.execute("ALTER TABLE processed_videos ADD COLUMN storage_url TEXT")
        cursor.execute("ALTER TABLE processed_videos ADD COLUMN storage_path TEXT")
        cursor.execute("ALTER TABLE processed_videos ADD COLUMN storage_type TEXT")
        logger.info("Added storage fields to processed_videos table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.debug("Storage columns already exist in processed_videos")
        else:
            raise

    conn.commit()


# List of migrations in order
MIGRATIONS: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, migration_v1_add_storage_fields),
    (2, migration_v2_add_processing_metadata),
]


def run_migrations(db_path: Path):
    """Run all pending migrations."""
    conn = sqlite3.connect(str(db_path))

    try:
        current_version = get_db_version(conn)
        latest_version = MIGRATIONS[-1][0] if MIGRATIONS else 0
        
        # Only log if we need to run migrations
        if current_version < latest_version:
            logger.info(f"Current database version: {current_version}")
            
            for version, migration_func in MIGRATIONS:
                if version > current_version:
                    logger.info(f"Running migration v{version}: {migration_func.__name__}")
                    migration_func(conn)
                    set_db_version(conn, version)
                    logger.info(f"Successfully applied migration v{version}")
            
            final_version = get_db_version(conn)
            logger.info(f"Database is now at version: {final_version}")
        else:
            # Database is already up to date, log at debug level only
            logger.debug(f"Database already at latest version: {current_version}")

    finally:
        conn.close()
