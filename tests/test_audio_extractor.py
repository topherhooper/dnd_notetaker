"""Tests for the simplified audio extractor"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import subprocess

from dnd_notetaker.audio_extractor import AudioExtractor


class TestAudioExtractor:
    """Test audio extraction functionality"""
    
    @pytest.fixture
    def extractor(self):
        """Create audio extractor instance"""
        return AudioExtractor()
    
    @pytest.fixture
    def temp_files(self):
        """Create temporary input/output files"""
        with tempfile.NamedTemporaryFile(suffix='.mp4') as video_file:
            with tempfile.NamedTemporaryFile(suffix='.mp3') as audio_file:
                yield Path(video_file.name), Path(audio_file.name)
    
    @patch('subprocess.run')
    def test_extract_success(self, mock_run, extractor, temp_files):
        """Test successful audio extraction"""
        video_path, audio_path = temp_files
        
        # Create the video file
        video_path.write_text("fake video")
        
        # Mock successful ffmpeg run
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        # Simulate ffmpeg creating the output file
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = lambda: audio_path.write_text("fake audio") or True
            
            # Run extraction
            extractor.extract(video_path, audio_path)
        
        # Verify ffmpeg was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        
        assert args[0] == 'ffmpeg'
        assert '-i' in args
        assert str(video_path) in args
        assert str(audio_path) in args
        assert '-vn' in args  # No video
        assert '-acodec' in args
        assert 'libmp3lame' in args
        assert '-b:a' in args
        assert '128k' in args
        assert '-ar' in args
        assert '44100' in args
        assert '-ac' in args
        assert '1' in args  # Mono
        assert '-y' in args  # Overwrite
    
    @patch('subprocess.run')
    def test_extract_ffmpeg_error(self, mock_run, extractor, temp_files):
        """Test handling of ffmpeg errors"""
        video_path, audio_path = temp_files
        
        # Mock ffmpeg failure
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffmpeg', stderr="FFmpeg error message"
        )
        
        # Run extraction and expect error
        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            extractor.extract(video_path, audio_path)
    
    @patch('subprocess.run')
    def test_extract_ffmpeg_not_found(self, mock_run, extractor, temp_files):
        """Test handling when ffmpeg is not installed"""
        video_path, audio_path = temp_files
        
        # Mock ffmpeg not found
        mock_run.side_effect = FileNotFoundError()
        
        # Run extraction and expect error
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            extractor.extract(video_path, audio_path)
    
    @patch('subprocess.run')
    def test_extract_output_not_created(self, mock_run, extractor):
        """Test error when output file is not created"""
        # Create temporary paths that don't use context managers
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            audio_path = Path(temp_dir) / "audio.mp3"
            
            # Create the video file
            video_path.write_text("fake video")
            
            # Mock successful ffmpeg run but no output file
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )
            
            # Run extraction and expect error
            with pytest.raises(RuntimeError, match="output file not created"):
                extractor.extract(video_path, audio_path)
    
    @patch('subprocess.run')
    @patch('pathlib.Path.mkdir')
    def test_extract_creates_output_directory(self, mock_mkdir, mock_run, extractor):
        """Test that output directory is created if needed"""
        video_path = Path("/tmp/video.mp4")
        audio_path = Path("/tmp/new_dir/audio.mp3")
        
        # Mock successful run
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock file operations
        with patch('pathlib.Path.exists') as mock_exists:
            with patch('pathlib.Path.stat') as mock_stat:
                # First call checks if output exists (for verification), should return True
                mock_exists.return_value = True
                mock_stat.return_value.st_size = 1024
                
                extractor.extract(video_path, audio_path)
        
        # Verify directory creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)