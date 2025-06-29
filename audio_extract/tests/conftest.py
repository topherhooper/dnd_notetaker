"""Pytest configuration for audio_extract tests."""

import sys
from pathlib import Path

# Add the parent directory to the Python path so tests can import audio_extract
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    class Config:
        def __init__(self):
            self.dry_run = False
    
    return Config()