"""Custom exceptions for audio extraction operations."""


class AudioExtractionError(Exception):
    """Base exception for all audio extraction errors."""
    pass


class FFmpegNotFoundError(AudioExtractionError):
    """Raised when FFmpeg is not installed or not found in PATH."""
    
    def __init__(self, message=None):
        if message is None:
            message = (
                "FFmpeg not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )
        super().__init__(message)


class InvalidAudioFileError(AudioExtractionError):
    """Raised when an audio file is invalid or cannot be processed."""
    
    def __init__(self, file_path, message=None):
        self.file_path = file_path
        if message is None:
            message = f"Invalid audio file: {file_path}"
        super().__init__(message)


class ChunkingError(AudioExtractionError):
    """Raised when audio chunking fails."""
    
    def __init__(self, message, chunk_num=None):
        self.chunk_num = chunk_num
        super().__init__(message)


class TrackingError(AudioExtractionError):
    """Raised when there's an issue with the processing tracker database."""
    pass