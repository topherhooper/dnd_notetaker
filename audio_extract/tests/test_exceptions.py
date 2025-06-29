"""Tests for custom exceptions in audio_extract module."""

import pytest
from audio_extract.exceptions import (
    AudioExtractionError,
    FFmpegNotFoundError,
    InvalidAudioFileError,
    ChunkingError,
    TrackingError
)


class TestExceptions:
    """Test custom exception classes."""
    
    def test_audio_extraction_error_base(self):
        """Test base AudioExtractionError."""
        with pytest.raises(AudioExtractionError) as exc_info:
            raise AudioExtractionError("Test error")
        
        assert str(exc_info.value) == "Test error"
        assert isinstance(exc_info.value, Exception)
    
    def test_ffmpeg_not_found_error(self):
        """Test FFmpegNotFoundError."""
        with pytest.raises(FFmpegNotFoundError) as exc_info:
            raise FFmpegNotFoundError()
        
        assert "FFmpeg" in str(exc_info.value)
        assert isinstance(exc_info.value, AudioExtractionError)
    
    def test_invalid_audio_file_error(self):
        """Test InvalidAudioFileError with file path."""
        test_path = "/path/to/invalid.mp3"
        with pytest.raises(InvalidAudioFileError) as exc_info:
            raise InvalidAudioFileError(test_path)
        
        assert test_path in str(exc_info.value)
        assert isinstance(exc_info.value, AudioExtractionError)
    
    def test_chunking_error(self):
        """Test ChunkingError with details."""
        with pytest.raises(ChunkingError) as exc_info:
            raise ChunkingError("Failed to split audio", chunk_num=3)
        
        assert "Failed to split audio" in str(exc_info.value)
        assert exc_info.value.chunk_num == 3
        assert isinstance(exc_info.value, AudioExtractionError)
    
    def test_tracking_error(self):
        """Test TrackingError."""
        with pytest.raises(TrackingError) as exc_info:
            raise TrackingError("Database connection failed")
        
        assert "Database connection failed" in str(exc_info.value)
        assert isinstance(exc_info.value, AudioExtractionError)
    
    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from AudioExtractionError."""
        exceptions = [
            FFmpegNotFoundError,
            InvalidAudioFileError,
            ChunkingError,
            TrackingError
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, AudioExtractionError)