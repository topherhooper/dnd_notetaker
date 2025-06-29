"""Audio chunking functionality for splitting large files."""

import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Callable

from .utils import verify_audio_file, get_audio_duration
from .exceptions import ChunkingError, InvalidAudioFileError


logger = logging.getLogger(__name__)


class AudioChunker:
    """Split large audio files into smaller chunks."""
    
    def __init__(self, max_size_mb: int = 24, chunk_duration_minutes: int = 15):
        """Initialize AudioChunker.
        
        Args:
            max_size_mb: Maximum chunk size in MB (default: 24MB)
            chunk_duration_minutes: Target chunk duration in minutes (default: 15)
        """
        self.max_chunk_size = max_size_mb * 1024 * 1024
        self.chunk_duration = chunk_duration_minutes * 60  # Convert to seconds
        self.temp_dirs = []  # Track temporary directories for cleanup
    
    def split(
        self, 
        audio_path: Path, 
        output_dir: Path,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> List[Path]:
        """Split audio file into chunks.
        
        Args:
            audio_path: Path to audio file to split
            output_dir: Directory to store chunks
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of paths to chunk files
            
        Raises:
            InvalidAudioFileError: If audio file is invalid
            ChunkingError: If splitting fails
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        
        logger.info(f"Processing audio file: {audio_path}")
        
        # Verify input file
        verify_audio_file(audio_path)
        
        # Check file size
        try:
            file_size = os.path.getsize(audio_path)
            logger.debug(f"Audio file size: {file_size/1024/1024:.1f}MB")
            
            # If file is small enough, return as is
            if file_size <= self.max_chunk_size:
                logger.info("Audio file is within size limit, no splitting needed")
                if progress_callback:
                    progress_callback(100)
                return [audio_path]
        except OSError as e:
            raise InvalidAudioFileError(str(audio_path), f"Cannot access file: {e}")
        
        # Get duration
        duration_seconds = get_audio_duration(audio_path)
        if duration_seconds is None:
            logger.warning("Could not determine duration, estimating from file size")
            # Estimate based on typical MP3 bitrate (128 kbps)
            estimated_duration = (file_size * 8) / (128 * 1000)  # seconds
            duration_seconds = estimated_duration
        
        logger.debug(f"Audio duration: {duration_seconds/60:.1f} minutes")
        
        # Calculate number of chunks
        num_chunks = max(1, int((duration_seconds + self.chunk_duration - 1) // self.chunk_duration))
        
        # If only one chunk needed, return original file
        if num_chunks == 1:
            logger.info("Audio duration suggests no splitting needed")
            if progress_callback:
                progress_callback(100)
            return [audio_path]
        
        logger.info(f"Splitting into {num_chunks} chunks (~{self.chunk_duration//60} minutes each)")
        
        # Create temporary directory for chunks
        temp_dir = self._create_temp_dir(output_dir)
        chunk_paths = []
        
        try:
            # Split using ffmpeg
            for i in range(num_chunks):
                if progress_callback:
                    progress = int((i / num_chunks) * 100)
                    progress_callback(progress)
                
                start_time = i * self.chunk_duration
                # Make sure we don't exceed the actual duration
                chunk_duration = min(self.chunk_duration, duration_seconds - start_time)
                
                chunk_path = self._split_chunk(
                    audio_path, temp_dir, start_time, chunk_duration, i
                )
                
                # Verify chunk was created
                if chunk_path.exists():
                    chunk_size = os.path.getsize(chunk_path)
                    logger.debug(f"Chunk {i} size: {chunk_size/1024/1024:.2f}MB")
                    chunk_paths.append(chunk_path)
                else:
                    raise ChunkingError(
                        f"Failed to create chunk {i}",
                        chunk_num=i
                    )
            
            if progress_callback:
                progress_callback(100)
            
            logger.info(f"Successfully split audio into {len(chunk_paths)} chunks")
            return chunk_paths
            
        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            # Clean up on error
            self.cleanup()
            if isinstance(e, ChunkingError):
                raise
            raise ChunkingError(str(e))
    
    def _split_chunk(
        self,
        audio_path: Path,
        output_dir: Path,
        start_seconds: float,
        duration_seconds: float,
        chunk_num: int
    ) -> Path:
        """Split a single chunk using ffmpeg.
        
        Args:
            audio_path: Input audio file
            output_dir: Output directory
            start_seconds: Start time in seconds
            duration_seconds: Duration in seconds
            chunk_num: Chunk number (0-based)
            
        Returns:
            Path to created chunk file
            
        Raises:
            ChunkingError: If ffmpeg fails
        """
        chunk_path = output_dir / f"chunk_{chunk_num}.mp3"
        
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-ss', str(start_seconds),
            '-t', str(duration_seconds),
            '-acodec', 'mp3',
            '-y',  # Overwrite output files
            str(chunk_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ChunkingError(
                f"Failed to split chunk {chunk_num}: {result.stderr}",
                chunk_num=chunk_num
            )
        
        return chunk_path
    
    def _create_temp_dir(self, base_dir: Path) -> Path:
        """Create a temporary directory and track it for cleanup.
        
        Args:
            base_dir: Base directory to create temp dir in
            
        Returns:
            Path to created temporary directory
        """
        # Create a subdirectory in the provided base directory
        temp_dir = base_dir / "audio_chunks_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self):
        """Clean up any temporary directories created."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                logger.debug(f"Cleaning up temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()