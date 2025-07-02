"""Tests for AudioExtractor in audio_extract module."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
import subprocess

from audio_extract.extractor import AudioExtractor
from audio_extract.exceptions import AudioExtractionError, FFmpegNotFoundError


class TestAudioExtractor:
    """Test AudioExtractor functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.dry_run = False
        return config

    @pytest.fixture
    def extractor(self, mock_config):
        """Create an AudioExtractor instance."""
        return AudioExtractor(config=mock_config)

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    def test_extractor_initialization(self, mock_verify):
        """Test extractor initialization verifies FFmpeg."""
        extractor = AudioExtractor()
        mock_verify.assert_called_once()

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.stat")
    def test_extract_success(self, mock_stat, mock_mkdir, mock_exists, mock_run, mock_verify):
        """Test successful audio extraction."""
        extractor = AudioExtractor()
        video_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/output/audio.mp3")

        # Mock successful extraction
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_stat.return_value = Mock(st_size=5 * 1024 * 1024)  # 5MB

        extractor.extract(video_path, output_path)

        # Verify FFmpeg was called with correct arguments
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert str(video_path) in cmd
        assert str(output_path) in cmd
        assert "-vn" in cmd  # No video
        assert "-acodec" in cmd
        assert "libmp3lame" in cmd

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    def test_extract_dry_run(self, mock_verify, mock_config, capsys):
        """Test extraction in dry-run mode."""
        mock_config.dry_run = True
        extractor = AudioExtractor(config=mock_config)

        video_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/output/audio.mp3")

        extractor.extract(video_path, output_path)

        # Check dry-run output
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would extract audio" in captured.out
        assert str(video_path) in captured.out
        assert str(output_path) in captured.out

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    @patch("subprocess.run")
    @patch("pathlib.Path.mkdir")
    def test_extract_ffmpeg_error(self, mock_mkdir, mock_run, mock_verify):
        """Test extraction when FFmpeg fails."""
        extractor = AudioExtractor()
        video_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/output/audio.mp3")

        # Mock FFmpeg failure
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error: Invalid input file")

        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.extract(video_path, output_path)

        assert "FFmpeg failed" in str(exc_info.value)
        assert "Invalid input file" in str(exc_info.value)

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_extract_output_not_created(self, mock_mkdir, mock_exists, mock_run, mock_verify):
        """Test extraction when output file is not created."""
        extractor = AudioExtractor()
        video_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/output/audio.mp3")

        # Mock successful run but no output file
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = False

        with pytest.raises(AudioExtractionError) as exc_info:
            extractor.extract(video_path, output_path)

        assert "output file not created" in str(exc_info.value)

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.mkdir")
    def test_extract_with_progress_callback(
        self, mock_mkdir, mock_stat, mock_exists, mock_run, mock_verify
    ):
        """Test extraction with progress callback."""
        extractor = AudioExtractor()
        video_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/output/audio.mp3")

        # Mock successful extraction
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_stat.return_value = Mock(st_size=5 * 1024 * 1024)  # 5MB

        progress_values = []

        def progress_callback(percent):
            progress_values.append(percent)

        extractor.extract(video_path, output_path, progress_callback=progress_callback)

        # Should have reported progress
        assert len(progress_values) > 0
        assert progress_values[-1] == 100  # Should end at 100%

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    @patch("audio_extract.extractor.get_audio_duration")
    def test_get_video_info(self, mock_duration, mock_verify):
        """Test getting video information."""
        extractor = AudioExtractor()
        video_path = Path("/path/to/video.mp4")

        mock_duration.return_value = 120.5

        info = extractor.get_video_info(video_path)

        assert info["duration"] == 120.5
        assert info["duration_formatted"] == "0:02:00"

    @patch("audio_extract.extractor.verify_ffmpeg_installed")
    def test_extract_with_custom_options(self, mock_verify):
        """Test extraction with custom audio options."""
        extractor = AudioExtractor(bitrate="192k", sample_rate=48000, channels=2)

        # Check that options were stored
        assert extractor.bitrate == "192k"
        assert extractor.sample_rate == 48000
        assert extractor.channels == 2
