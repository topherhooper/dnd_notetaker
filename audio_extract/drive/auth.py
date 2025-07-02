"""Google Drive authentication helpers."""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Union

from google.auth import exceptions
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class DriveAuth:
    """Handle Google Drive authentication."""

    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self, credentials_path: Optional[Union[str, Path]] = None):
        """Initialize Drive authentication.

        Args:
            credentials_path: Path to service account JSON file.
                            If not provided, will check environment variables.
        """
        self.credentials_path = credentials_path
        self._credentials = None

    def get_credentials(self):
        """Get Google credentials.

        Returns:
            google.auth.credentials.Credentials: Authenticated credentials

        Raises:
            ValueError: If no credentials are found
            exceptions.GoogleAuthError: If authentication fails
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to refresh if expired
        if self._credentials and self._credentials.expired:
            self._credentials.refresh(Request())
            return self._credentials

        # Load new credentials
        self._credentials = self._load_credentials()
        return self._credentials

    def _load_credentials(self):
        """Load credentials from file or environment.

        Returns:
            google.auth.credentials.Credentials: Loaded credentials

        Raises:
            ValueError: If no credentials source is found
        """
        # Try explicit path first
        if self.credentials_path:
            return self._load_from_file(self.credentials_path)

        # Try environment variable
        env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if env_path:
            logger.info("Using credentials from GOOGLE_APPLICATION_CREDENTIALS")
            return self._load_from_file(env_path)

        # Try common locations
        common_paths = [
            Path.home() / ".config" / "gcloud" / "service_account.json",
            Path("service_account.json"),
            Path("credentials.json"),
        ]

        for path in common_paths:
            if path.exists():
                logger.info(f"Found credentials at: {path}")
                return self._load_from_file(path)

        raise ValueError(
            "No Google credentials found. Please provide credentials_path or "
            "set GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )

    def _load_from_file(self, path: Union[str, Path]):
        """Load service account credentials from file.

        Args:
            path: Path to service account JSON file

        Returns:
            google.auth.credentials.Credentials: Service account credentials

        Raises:
            ValueError: If file is invalid
        """
        path = Path(path)
        if not path.exists():
            raise ValueError(f"Credentials file not found: {path}")

        credentials = service_account.Credentials.from_service_account_file(
            str(path), scopes=self.SCOPES
        )
        logger.info("Successfully loaded service account credentials")
        return credentials

    def validate(self) -> bool:
        """Validate that credentials are working.

        Returns:
            bool: True if credentials are valid and working
        """
        creds = self.get_credentials()
        # Force a refresh to validate
        if not creds.valid:
            creds.refresh(Request())
        return True
