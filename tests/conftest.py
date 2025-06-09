"""Shared test fixtures and configuration for pytest"""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Sample configuration dictionary"""
    return {
        "openai_api_key": "test_openai_key",
        "email": "test@example.com",
        "email_password": "test_password",
        "google_credentials_path": ".credentials/credentials.json",
    }


@pytest.fixture
def sample_transcript():
    """Sample transcript text for testing"""
    return """DM: Welcome back to our D&D session. Last time, you were exploring the ancient ruins.
Player 1: I want to search for traps.
DM: Roll investigation.
Player 1: I rolled a 15 plus 3, so 18.
DM: You notice a pressure plate in the floor ahead.
Player 2: Can I cast detect magic?
DM: Sure, make an arcana check.
Player 2: Natural 20!
DM: The entire corridor glows with a faint magical aura. You sense evocation magic."""


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a mock audio file"""
    audio_path = os.path.join(temp_dir, "test_audio.mp3")
    with open(audio_path, "wb") as f:
        f.write(b"fake audio data")
    return audio_path


@pytest.fixture
def mock_video_file(temp_dir):
    """Create a mock video file"""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake video data")
    return video_path
