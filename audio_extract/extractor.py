"""Core audio extraction functionality."""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from .utils import (
    verify_ffmpeg_installed,
    build_ffmpeg_extract_command,
    get_audio_duration,
    format_duration,
)
from .exceptions import AudioExtractionError, FFmpegNotFoundError


logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extract audio from video files using FFmpeg."""

    def __init__(
        self, config=None, bitrate: str = "128k", sample_rate: int = 44100, channels: int = 1
    ):
        """Initialize AudioExtractor.

        Args:
            config: Optional configuration object with dry_run attribute
            bitrate: Audio bitrate (default: 128k)
            sample_rate: Audio sample rate (default: 44100)
            channels: Number of audio channels (default: 1 for mono)
        """
        self.config = config
        self.bitrate = bitrate
        self.sample_rate = sample_rate
        self.channels = channels

        # Verify FFmpeg is installed
        verify_ffmpeg_installed()

    def extract(
        self,
        video_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Extract audio from video file.

        Args:
            video_path: Path to input video file
            output_path: Path to output audio file (mp3)
            progress_callback: Optional callback function for progress updates

        Raises:
            AudioExtractionError: If extraction fails
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if self.config and getattr(self.config, "dry_run", False):
            # Dry run mode - just show what would happen
            print(f"[DRY RUN] Would extract audio using FFmpeg:")
            print(f"  Input: {video_path}")
            print(f"  Output: {output_path}")
            cmd = build_ffmpeg_extract_command(
                video_path,
                output_path,
                bitrate=self.bitrate,
                sample_rate=self.sample_rate,
                channels=self.channels,
            )
            print(f"  Command: {' '.join(cmd)}")
            return

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        cmd = build_ffmpeg_extract_command(
            video_path,
            output_path,
            bitrate=self.bitrate,
            sample_rate=self.sample_rate,
            channels=self.channels,
        )

        # Run FFmpeg
        if progress_callback:
            self._run_with_progress(cmd, progress_callback)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                raise AudioExtractionError(f"FFmpeg failed: {result.stderr}")

        # Verify output file was created
        if not output_path.exists():
            raise AudioExtractionError("Audio extraction failed - output file not created")

        # Log file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Audio extracted successfully ({size_mb:.1f} MB)")

    def _run_with_progress(self, cmd: list, progress_callback: Callable[[int], None]) -> None:
        """Run FFmpeg with progress tracking.

        Args:
            cmd: FFmpeg command to run
            progress_callback: Callback for progress updates
        """
        # For simplicity, just report 0% and 100%
        # A full implementation would parse FFmpeg's progress output
        progress_callback(0)

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise AudioExtractionError(f"FFmpeg failed: {result.stderr}")

        progress_callback(100)

    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get information about a video file.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video information
        """
        video_path = Path(video_path)
        duration = get_audio_duration(video_path)

        return {
            "path": str(video_path),
            "duration": duration,
            "duration_formatted": format_duration(duration),
        }
