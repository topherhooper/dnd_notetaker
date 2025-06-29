"""Tests for utilities in audio_extract module."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
import subprocess

from audio_extract.utils import (
    verify_ffmpeg_installed,
    build_ffmpeg_extract_command,
    get_audio_duration,
    verify_audio_file,
    get_file_hash,
    format_duration
)
from audio_extract.exceptions import FFmpegNotFoundError, InvalidAudioFileError


class TestFFmpegUtils:
    """Test FFmpeg-related utilities."""
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_installed_success(self, mock_run):
        """Test successful FFmpeg verification."""
        mock_run.return_value = Mock(returncode=0)
        
        # Should not raise exception
        verify_ffmpeg_installed()
        
        mock_run.assert_called_once_with(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_installed_not_found(self, mock_run):
        """Test FFmpeg not found."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(FFmpegNotFoundError):
            verify_ffmpeg_installed()
    
    def test_build_ffmpeg_extract_command(self):
        """Test building FFmpeg extraction command."""
        input_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/audio.mp3")
        
        cmd = build_ffmpeg_extract_command(input_path, output_path)
        
        expected = [
            'ffmpeg',
            '-i', str(input_path),
            '-vn',
            '-acodec', 'libmp3lame',
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '1',
            '-y',
            str(output_path)
        ]
        
        assert cmd == expected
    
    def test_build_ffmpeg_extract_command_with_options(self):
        """Test building FFmpeg command with custom options."""
        input_path = Path("/path/to/video.mp4")
        output_path = Path("/path/to/audio.mp3")
        
        cmd = build_ffmpeg_extract_command(
            input_path, 
            output_path,
            bitrate='192k',
            sample_rate=48000,
            channels=2
        )
        
        assert '-b:a' in cmd
        assert '192k' in cmd
        assert '-ar' in cmd
        assert '48000' in cmd
        assert '-ac' in cmd
        assert '2' in cmd


class TestAudioUtils:
    """Test audio file utilities."""
    
    @patch('subprocess.run')
    def test_get_audio_duration_success(self, mock_run):
        """Test getting audio duration."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="120.5\n"
        )
        
        duration = get_audio_duration(Path("/path/to/audio.mp3"))
        
        assert duration == 120.5
        assert mock_run.called
        assert 'ffprobe' in mock_run.call_args[0][0]
    
    @patch('subprocess.run')
    def test_get_audio_duration_failure(self, mock_run):
        """Test getting audio duration when ffprobe fails."""
        mock_run.return_value = Mock(returncode=1, stdout="")
        
        duration = get_audio_duration(Path("/path/to/audio.mp3"))
        
        assert duration is None
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('os.access')
    def test_verify_audio_file_success(self, mock_access, mock_is_file, mock_exists):
        """Test successful audio file verification."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_access.return_value = True
        
        # Should not raise exception
        verify_audio_file(Path("/path/to/audio.mp3"))
    
    @patch('pathlib.Path.exists')
    def test_verify_audio_file_not_exists(self, mock_exists):
        """Test verifying non-existent file."""
        mock_exists.return_value = False
        
        with pytest.raises(InvalidAudioFileError) as exc_info:
            verify_audio_file(Path("/path/to/missing.mp3"))
        
        assert "not found" in str(exc_info.value)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_verify_audio_file_not_file(self, mock_is_file, mock_exists):
        """Test verifying a directory instead of file."""
        mock_exists.return_value = True
        mock_is_file.return_value = False
        
        with pytest.raises(InvalidAudioFileError) as exc_info:
            verify_audio_file(Path("/path/to/directory"))
        
        assert "not a file" in str(exc_info.value)


class TestHashUtils:
    """Test file hashing utilities."""
    
    @patch('pathlib.Path.open')
    @patch('pathlib.Path.exists')
    def test_get_file_hash(self, mock_exists, mock_open):
        """Test getting file hash."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.side_effect = [b'test data', b'']
        mock_open.return_value.__enter__.return_value = mock_file
        
        hash_value = get_file_hash(Path("/path/to/file.mp3"))
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hex length
    
    @patch('pathlib.Path.exists')
    def test_get_file_hash_missing_file(self, mock_exists):
        """Test hashing non-existent file."""
        mock_exists.return_value = False
        
        with pytest.raises(InvalidAudioFileError):
            get_file_hash(Path("/path/to/missing.mp3"))


class TestFormatUtils:
    """Test formatting utilities."""
    
    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        assert format_duration(45) == "0:00:45"
        assert format_duration(0) == "0:00:00"
    
    def test_format_duration_minutes(self):
        """Test formatting duration with minutes."""
        assert format_duration(125) == "0:02:05"
        assert format_duration(3600) == "1:00:00"
    
    def test_format_duration_hours(self):
        """Test formatting duration with hours."""
        assert format_duration(3661) == "1:01:01"
        assert format_duration(7323) == "2:02:03"
    
    def test_format_duration_none(self):
        """Test formatting None duration."""
        assert format_duration(None) == "Unknown"