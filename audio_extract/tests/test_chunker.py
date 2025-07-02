"""Tests for AudioChunker in audio_extract module."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
import tempfile
import shutil

from audio_extract.chunker import AudioChunker
from audio_extract.exceptions import ChunkingError, InvalidAudioFileError


class TestAudioChunker:
    """Test AudioChunker functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def chunker(self):
        """Create an AudioChunker instance."""
        return AudioChunker()

    def test_chunker_initialization(self):
        """Test chunker initialization with defaults."""
        chunker = AudioChunker()
        assert chunker.max_chunk_size == 24 * 1024 * 1024  # 24MB
        assert chunker.chunk_duration == 15 * 60  # 15 minutes

    def test_chunker_custom_settings(self):
        """Test chunker with custom settings."""
        chunker = AudioChunker(max_size_mb=10, chunk_duration_minutes=5)
        assert chunker.max_chunk_size == 10 * 1024 * 1024
        assert chunker.chunk_duration == 5 * 60

    @patch("audio_extract.chunker.verify_audio_file")
    @patch("os.path.getsize")
    def test_split_small_file(self, mock_getsize, mock_verify, chunker, temp_dir):
        """Test splitting a file that's already small enough."""
        audio_path = temp_dir / "small.mp3"
        audio_path.touch()

        # Mock file size as 10MB (under 24MB limit)
        mock_getsize.return_value = 10 * 1024 * 1024

        chunks = chunker.split(audio_path, temp_dir)

        # Should return original file
        assert len(chunks) == 1
        assert chunks[0] == audio_path

    @patch("audio_extract.chunker.verify_audio_file")
    @patch("audio_extract.chunker.get_audio_duration")
    @patch("os.path.getsize")
    @patch("subprocess.run")
    def test_split_large_file(
        self, mock_run, mock_getsize, mock_duration, mock_verify, chunker, temp_dir
    ):
        """Test splitting a large file into chunks."""
        audio_path = temp_dir / "large.mp3"
        audio_path.touch()

        # Mock file size as 100MB and duration as 45 minutes
        mock_getsize.return_value = 100 * 1024 * 1024
        mock_duration.return_value = 45 * 60  # 45 minutes

        # Mock successful ffmpeg runs
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create mock chunk files in temp directory
        temp_chunks_dir = temp_dir / "audio_chunks_temp"
        temp_chunks_dir.mkdir(exist_ok=True)
        for i in range(3):
            chunk_path = temp_chunks_dir / f"chunk_{i}.mp3"
            chunk_path.touch()

        chunks = chunker.split(audio_path, temp_dir)

        # Should create 3 chunks (45 min / 15 min = 3)
        assert len(chunks) == 3
        assert all(Path(chunk).name.startswith("chunk_") for chunk in chunks)

        # Verify ffmpeg was called 3 times
        assert mock_run.call_count == 3

    @patch("audio_extract.chunker.verify_audio_file")
    @patch("audio_extract.chunker.get_audio_duration")
    @patch("os.path.getsize")
    @patch("subprocess.run")
    def test_split_with_ffmpeg_error(
        self, mock_run, mock_getsize, mock_duration, mock_verify, chunker, temp_dir
    ):
        """Test handling of ffmpeg errors during splitting."""
        audio_path = temp_dir / "audio.mp3"
        audio_path.touch()

        mock_getsize.return_value = 50 * 1024 * 1024
        mock_duration.return_value = 30 * 60

        # Mock ffmpeg failure
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="FFmpeg error")

        with pytest.raises(ChunkingError) as exc_info:
            chunker.split(audio_path, temp_dir)

        assert "Failed to split chunk" in str(exc_info.value)
        assert exc_info.value.chunk_num == 0

    @patch("audio_extract.chunker.verify_audio_file")
    def test_split_missing_file(self, mock_verify, chunker, temp_dir):
        """Test splitting a non-existent file."""
        audio_path = temp_dir / "missing.mp3"

        # Make verify_audio_file raise exception
        mock_verify.side_effect = InvalidAudioFileError(str(audio_path))

        with pytest.raises(InvalidAudioFileError):
            chunker.split(audio_path, temp_dir)

    @patch("audio_extract.chunker.verify_audio_file")
    @patch("audio_extract.chunker.get_audio_duration")
    @patch("os.path.getsize")
    @patch("subprocess.run")
    def test_split_with_unknown_duration(
        self, mock_run, mock_getsize, mock_duration, mock_verify, chunker, temp_dir
    ):
        """Test splitting when duration cannot be determined."""
        audio_path = temp_dir / "audio.mp3"
        audio_path.touch()

        mock_getsize.return_value = 50 * 1024 * 1024
        mock_duration.return_value = None  # Unknown duration

        # Mock successful ffmpeg runs
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create mock chunk files
        for i in range(4):
            chunk_path = temp_dir / "audio_chunks_temp" / f"chunk_{i}.mp3"
            chunk_path.parent.mkdir(exist_ok=True)
            chunk_path.touch()

        # Should fall back to size-based estimation
        chunks = chunker.split(audio_path, temp_dir)

        # With 128kbps estimate, 50MB ≈ 52 minutes, so should split
        assert len(chunks) > 1

    def test_cleanup_on_error(self, chunker, temp_dir):
        """Test that temporary files are cleaned up on error."""
        # Create a mock temp directory tracker
        chunker.temp_dirs = [temp_dir / "temp_chunks"]
        (temp_dir / "temp_chunks").mkdir()

        # Create some temp files
        for i in range(3):
            (temp_dir / "temp_chunks" / f"chunk_{i}.mp3").touch()

        # Cleanup should remove temp directory
        chunker.cleanup()

        assert not (temp_dir / "temp_chunks").exists()

    @patch("audio_extract.chunker.verify_audio_file")
    @patch("os.path.getsize")
    def test_split_with_progress_callback(self, mock_getsize, mock_verify, chunker, temp_dir):
        """Test splitting with progress callback."""
        audio_path = temp_dir / "audio.mp3"
        audio_path.touch()

        mock_getsize.return_value = 10 * 1024 * 1024

        progress_values = []

        def progress_callback(percent):
            progress_values.append(percent)

        chunks = chunker.split(audio_path, temp_dir, progress_callback=progress_callback)

        # Should have reported some progress
        assert len(progress_values) > 0
        assert progress_values[-1] == 100
