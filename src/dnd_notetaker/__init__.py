"""
D&D Notetaker - Automated D&D session recording processor

This package provides tools for processing D&D session recordings:
- Download recordings from email/Google Drive
- Extract audio from video files
- Transcribe audio using OpenAI Whisper
- Process transcripts into structured notes using GPT-4
- Upload notes to Google Docs
"""

__version__ = "1.0.0"

from .audio_processor import AudioProcessor
from .docs_uploader import DocsUploader
from .email_handler import EmailHandler

# Import main components for easier access
from .main import MeetingProcessor
from .transcriber import Transcriber
from .transcript_processor import TranscriptProcessor
from .utils import cleanup_old_temp_directories, list_temp_directories, setup_logging

__all__ = [
    "MeetingProcessor",
    "AudioProcessor",
    "Transcriber",
    "TranscriptProcessor",
    "DocsUploader",
    "EmailHandler",
    "setup_logging",
    "cleanup_old_temp_directories",
    "list_temp_directories",
]
