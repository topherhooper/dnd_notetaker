"""Factory for creating storage adapters."""

from typing import Dict, Any
import logging

from .base import StorageAdapter
from .local_storage import LocalStorageAdapter
from .gcs_storage import GCSStorageAdapter


logger = logging.getLogger(__name__)


class StorageFactory:
    """Factory for creating storage adapters based on configuration."""

    @staticmethod
    def create(config: Dict[str, Any]) -> StorageAdapter:
        """Create a storage adapter from configuration.

        Args:
            config: Storage configuration dictionary with structure:
                {
                    'type': 'local' or 'gcs',
                    'local': {
                        'path': '/path/to/storage'
                    },
                    'gcs': {
                        'bucket_name': 'my-bucket',
                        'credentials_path': '/path/to/creds.json',
                        'public_access': True,
                        'url_expiration_hours': 24
                    }
                }

        Returns:
            Configured storage adapter

        Raises:
            ValueError: If storage type is not supported
        """
        storage_type = config.get("type", "local")

        if storage_type == "local":
            local_config = config.get("local", {})
            base_path = local_config.get("path", "./output")

            logger.info(f"Creating local storage adapter at: {base_path}")
            return LocalStorageAdapter(base_path=base_path)

        elif storage_type == "gcs":
            gcs_config = config.get("gcs", {})

            # Required parameters
            bucket_name = gcs_config.get("bucket_name")
            credentials_path = gcs_config.get("credentials_path")

            if not bucket_name or not credentials_path:
                raise ValueError("GCS storage requires 'bucket_name' and 'credentials_path'")

            # Optional parameters with defaults
            public_access = gcs_config.get("public_access", True)
            url_expiration_hours = gcs_config.get("url_expiration_hours", 24)

            logger.info(f"Creating GCS storage adapter for bucket: {bucket_name}")
            return GCSStorageAdapter(
                bucket_name=bucket_name,
                credentials_path=credentials_path,
                public_access=public_access,
                url_expiration_hours=url_expiration_hours,
            )

        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
