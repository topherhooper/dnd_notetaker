"""
D&D Notetaker - Automated D&D session recording processor

This package provides tools for processing D&D session recordings:
- Download recordings from Google Drive
- Extract audio from video files
- Transcribe audio using OpenAI Whisper
- Process transcripts into structured notes using GPT-4
- Upload notes to Google Docs
"""

__version__ = "2.0.0"

from .audio_processor import AudioProcessor
from .docs_uploader import DocsUploader
from .drive_handler import DriveHandler

# Import main components for easier access
from .transcriber import Transcriber
from .utils import setup_logging

# Import new simplified components
from .meet_processor import MeetProcessor
from .audio_extractor import AudioExtractor
from .note_generator import NoteGenerator
from .artifacts import Artifacts
from .simplified_drive_handler import SimplifiedDriveHandler
from .config import Config

__all__ = [
    # Legacy components
    "AudioProcessor",
    "Transcriber",
    "DocsUploader",
    "DriveHandler",
    "setup_logging",
    # New simplified components
    "MeetProcessor",
    "AudioExtractor",
    "NoteGenerator",
    "Artifacts",
    "SimplifiedDriveHandler",
    "Config",
]
