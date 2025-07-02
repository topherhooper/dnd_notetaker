"""Utility functions for audio extraction operations."""

import subprocess
import hashlib
import os
from pathlib import Path
from typing import Optional, List

from .exceptions import FFmpegNotFoundError, InvalidAudioFileError


def verify_ffmpeg_installed() -> None:
    """Verify that FFmpeg is installed and available.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found in PATH
    """
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegNotFoundError()
    except FileNotFoundError:
        raise FFmpegNotFoundError()


def build_ffmpeg_extract_command(
    input_path: Path,
    output_path: Path,
    bitrate: str = "128k",
    sample_rate: int = 44100,
    channels: int = 1,
) -> List[str]:
    """Build FFmpeg command for audio extraction.

    Args:
        input_path: Path to input video file
        output_path: Path to output audio file
        bitrate: Audio bitrate (default: 128k)
        sample_rate: Audio sample rate (default: 44100)
        channels: Number of audio channels (default: 1 for mono)

    Returns:
        List of command arguments for subprocess
    """
    return [
        "ffmpeg",
        "-i",
        str(input_path),
        "-vn",  # No video
        "-acodec",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        "-y",  # Overwrite output
        str(output_path),
    ]


def get_audio_duration(audio_path: Path) -> Optional[float]:
    """Get audio duration in seconds using ffprobe.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds, or None if unable to determine
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        pass

    return None


def verify_audio_file(file_path: Path) -> None:
    """Verify audio file exists and is accessible.

    Args:
        file_path: Path to audio file

    Raises:
        InvalidAudioFileError: If file is invalid or inaccessible
    """
    if not file_path.exists():
        raise InvalidAudioFileError(str(file_path), f"Audio file not found: {file_path}")

    if not file_path.is_file():
        raise InvalidAudioFileError(str(file_path), f"Path is not a file: {file_path}")

    if not os.access(file_path, os.R_OK):
        raise InvalidAudioFileError(str(file_path), f"No permission to read file: {file_path}")


def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use (default: sha256)

    Returns:
        Hex string of file hash

    Raises:
        InvalidAudioFileError: If file cannot be read
    """
    if not file_path.exists():
        raise InvalidAudioFileError(str(file_path), f"File not found: {file_path}")

    hash_func = hashlib.new(algorithm)

    try:
        with file_path.open("rb") as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except (IOError, OSError) as e:
        raise InvalidAudioFileError(str(file_path), f"Error reading file: {e}")


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1:23:45" or "Unknown" if None
    """
    if seconds is None:
        return "Unknown"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    return f"{hours}:{minutes:02d}:{secs:02d}"
