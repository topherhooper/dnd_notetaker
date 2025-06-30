"""Audio extraction module for D&D Notetaker.

This module provides functionality for extracting audio from video files,
chunking large audio files, tracking processing history, and monitoring
Google Drive for new recordings.
"""

# Import only what exists to allow incremental development
try:
    from .exceptions import (  # noqa: F401
        AudioExtractionError,
        FFmpegNotFoundError,
        InvalidAudioFileError,
        ChunkingError,
        TrackingError,
    )
except ImportError:
    pass

try:
    from .extractor import AudioExtractor  # noqa: F401
except ImportError:
    pass

try:
    from .chunker import AudioChunker  # noqa: F401
except ImportError:
    pass

try:
    from .tracker import ProcessingTracker  # noqa: F401
except ImportError:
    pass

try:
    from .config import Config  # noqa: F401
except ImportError:
    pass

try:
    from .drive import DriveAuth, DriveClient, DriveMonitor  # noqa: F401
except ImportError:
    pass

try:
    from .storage import (  # noqa: F401
        StorageAdapter,
        LocalStorageAdapter,
        GCSStorageAdapter,
        StorageFactory,
    )
except ImportError:
    pass

__version__ = "0.1.0"
