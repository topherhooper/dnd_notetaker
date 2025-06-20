"""Simplified configuration management for meet_notes"""

import os
import logging
import json
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)

class Config:
    """Simple configuration management"""
    
    def __init__(self, config_path: Optional[str] = None, dry_run: bool = False):
        self.dry_run = dry_run
        
        # Support environment variable for config location (useful for Docker)
        if config_path:
            self.config_file = Path(config_path)
            self.config_dir = self.config_file.parent
        else:
            env_config = os.environ.get("MEET_NOTES_CONFIG")
            if env_config:
                self.config_file = Path(env_config)
                self.config_dir = self.config_file.parent
            else:
                self.config_dir = Path(".credentials")
                self.config_file = self.config_dir / "config.json"
        self._config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default config
            default_config = {
                "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                "google_service_account": str(self.config_dir / "service_account.json"),
                "output_dir": "./meet_notes_output"
            }
            
            if not self.dry_run:
                # Ensure config directory exists
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
                # Save default config
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
            
            return default_config
    
    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key"""
        key = self._config.get("openai_api_key", "")
        if not key and not self.dry_run:
            raise ValueError(
                "OpenAI API key not configured.\n\n"
                "To fix this:\n"
                "1. Get your API key from: https://platform.openai.com/api-keys\n"
                "2. Edit .credentials/config.json\n"
                "3. Set \"openai_api_key\": \"sk-your-key-here\"\n\n"
                "See README.md for detailed instructions."
            )
        return key
    
    @property
    def service_account_path(self) -> Path:
        """Get Google service account path"""
        path = Path(self._config.get("google_service_account", ""))
        if not path.exists() and not self.dry_run:
            raise ValueError(
                f"Service account file not found: {path}\n\n"
                "To fix this:\n"
                "1. Create a Google Cloud service account\n"
                "2. Download the JSON key file\n" 
                "3. Save it to: .credentials/service_account.json\n"
                "4. Or update the path in: .credentials/config.json\n\n"
                "See README.md for detailed instructions."
            )
        return path
    
    @property
    def output_dir(self) -> Path:
        """Get output directory"""
        # Check if set via setter first
        if hasattr(self, '_output_dir_override'):
            path = self._output_dir_override
        # Check environment variable (for Docker)
        elif env_output := os.environ.get("MEET_NOTES_OUTPUT"):
            path = Path(env_output)
        else:
            path = Path(self._config.get("output_dir", "./meet_notes_output")).expanduser()
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @output_dir.setter
    def output_dir(self, value: Path):
        """Set output directory override"""
        self._output_dir_override = value