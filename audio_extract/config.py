"""Configuration management for audio_extract module."""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for audio_extract."""
    
    def __init__(self, config_path: Union[str, Path]):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self._config = self._load_config()
        self._apply_environment_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults.
        
        Returns:
            Configuration dictionary
        """
        # Load from file if found
        path = Path(self.config_path)
        assert path.exists(), f"Configuration file not found: {path}"
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                file_config = yaml.safe_load(f)
            else:
                file_config = json.load(f)
        
        # Deep merge with defaults
        logger.info(f"Loaded configuration from: {path}")
    
        return file_config
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        # Google Drive settings
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            self._config['google_drive']['service_account_file'] = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        if os.environ.get('AUDIO_EXTRACT_FOLDER_ID'):
            self._config['google_drive']['recordings_folder_id'] = os.environ['AUDIO_EXTRACT_FOLDER_ID']
        
        # Processing settings
        if os.environ.get('AUDIO_EXTRACT_OUTPUT_DIR'):
            self._config['processing']['output_directory'] = os.environ['AUDIO_EXTRACT_OUTPUT_DIR']
        
        # Monitoring settings
        if os.environ.get('AUDIO_EXTRACT_LOG_LEVEL'):
            self._config['monitoring']['log_level'] = os.environ['AUDIO_EXTRACT_LOG_LEVEL']
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Dot-separated key path (e.g., 'google_drive.check_interval_seconds')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value.
        
        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
    
    def save(self, path: Optional[Union[str, Path]] = None):
        """Save configuration to file.
        
        Args:
            path: Path to save to (uses original path if not specified)
        """
        save_path = Path(path or self.config_path)
        
        with open(save_path, 'w') as f:
            if save_path.suffix in ['.yaml', '.yml']:
                yaml.dump(self._config, f, default_flow_style=False)
            else:
                json.dump(self._config, f, indent=2)
        
        logger.info(f"Saved configuration to: {save_path}")
    
    def validate(self) -> List[str]:
        """Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required Google Drive settings
        if self.get('google_drive.recordings_folder_id') is None:
            errors.append("Google Drive folder ID not configured")
        
        # Check output directory
        output_dir = self.get('processing.output_directory')
        if not output_dir:
            errors.append("Output directory not configured")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Config(path={self.config_path})"