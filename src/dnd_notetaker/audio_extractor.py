"""Simplified audio extraction from video files"""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extract audio from video files using FFmpeg"""
    
    def __init__(self, config=None):
        """Initialize with optional config"""
        self.config = config
    
    def extract(self, video_path: Path, output_path: Path) -> None:
        """Extract audio from video file
        
        Args:
            video_path: Path to input video file
            output_path: Path to output audio file (mp3)
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            print(f"[DRY RUN] Would extract audio using FFmpeg:")
            print(f"  Input: {video_path}")
            print(f"  Output: {output_path}")
            print(f"  Command: ffmpeg -i {video_path} -vn -acodec libmp3lame -b:a 128k -ar 44100 -ac 1 {output_path}")
            return
            
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # FFmpeg command for audio extraction with optimization
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-b:a', '128k',  # Audio bitrate
            '-ar', '44100',  # Sample rate
            '-ac', '1',  # Mono audio (smaller file)
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        try:
            # Run FFmpeg with progress suppression
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Verify output file was created
            if not output_path.exists():
                raise RuntimeError(f"Audio extraction failed - output file not created")
                
            # Log file size
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Audio extracted successfully ({size_mb:.1f} MB)")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg failed: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg: https://ffmpeg.org/download.html")