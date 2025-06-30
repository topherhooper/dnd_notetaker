"""Tests for ProcessingTracker in audio_extract module."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json

from audio_extract.tracker import ProcessingTracker
from audio_extract.exceptions import TrackingError


class TestProcessingTracker:
    """Test ProcessingTracker functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_tracker.db"
        yield db_path
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def tracker(self, temp_db_path):
        """Create a ProcessingTracker instance with temporary database."""
        return ProcessingTracker(temp_db_path)

    def test_tracker_initialization(self, temp_db_path):
        """Test tracker initialization creates database."""
        tracker = ProcessingTracker(temp_db_path)
        assert temp_db_path.exists()
        tracker.close()

    def test_mark_processed_completed(self, tracker):
        """Test marking a video as successfully processed."""
        video_path = "/path/to/video.mp4"
        metadata = {"audio_path": "/path/to/audio.mp3", "duration": 120.5}

        tracker.mark_processed(video_path, status="completed", metadata=metadata)

        assert tracker.is_processed(video_path)
        result = tracker.get_metadata(video_path)
        assert result["status"] == "completed"
        assert result["metadata"]["audio_path"] == "/path/to/audio.mp3"

    def test_mark_processed_failed(self, tracker):
        """Test marking a video as failed."""
        video_path = "/path/to/video.mp4"
        error_metadata = {"error": "FFmpeg failed", "exit_code": 1}

        tracker.mark_processed(video_path, status="failed", metadata=error_metadata)

        # is_processed only returns True for completed status
        assert not tracker.is_processed(video_path)
        result = tracker.get_metadata(video_path)
        assert result["status"] == "failed"
        assert "FFmpeg failed" in result["metadata"]["error"]

    def test_is_processed_not_found(self, tracker):
        """Test checking unprocessed video."""
        assert not tracker.is_processed("/path/to/unprocessed.mp4")

    def test_get_metadata_not_found(self, tracker):
        """Test getting metadata for unprocessed video."""
        assert tracker.get_metadata("/path/to/unprocessed.mp4") is None

    def test_hash_based_tracking(self, tracker, tmp_path):
        """Test that tracker uses file hash for detection."""
        # Create a test file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"test video content")

        # Mark as processed
        tracker.mark_processed(str(video_file), status="completed")

        # Move the file
        moved_file = tmp_path / "moved_test.mp4"
        video_file.rename(moved_file)

        # Should still be detected as processed
        assert tracker.is_processed(str(moved_file))

    def test_get_recent_processed(self, tracker):
        """Test getting recently processed videos."""
        # Add some test data
        videos = [
            ("/video1.mp4", "completed"),
            ("/video2.mp4", "failed"),
            ("/video3.mp4", "completed"),
        ]

        for path, status in videos:
            tracker.mark_processed(path, status=status)

        # Get all recent (last 7 days should include all just added)
        recent = tracker.get_recent_processed(days=7)

        # Should include all 3 videos
        assert len(recent) == 3
        paths = [r["file_path"] for r in recent]
        assert "/video1.mp4" in paths
        assert "/video2.mp4" in paths
        assert "/video3.mp4" in paths

    def test_get_failed_videos(self, tracker):
        """Test getting failed videos."""
        # Add test data
        tracker.mark_processed("/video1.mp4", status="completed")
        tracker.mark_processed("/video2.mp4", status="failed", metadata={"error": "Test error 1"})
        tracker.mark_processed("/video3.mp4", status="failed", metadata={"error": "Test error 2"})

        failed = tracker.get_failed_videos()

        assert len(failed) == 2
        assert all(v["status"] == "failed" for v in failed)
        assert any(v["file_path"] == "/video2.mp4" for v in failed)
        assert any(v["file_path"] == "/video3.mp4" for v in failed)

    def test_reprocess_video(self, tracker):
        """Test marking a video for reprocessing."""
        video_path = "/path/to/video.mp4"

        # First mark as completed
        tracker.mark_processed(video_path, status="completed")
        assert tracker.is_processed(video_path)

        # Mark for reprocessing
        tracker.mark_for_reprocessing(video_path)
        assert not tracker.is_processed(video_path)

    def test_cleanup_old_entries(self, tracker):
        """Test cleaning up old database entries."""
        # Add old and new entries
        tracker.mark_processed("/old_video.mp4", status="completed")
        tracker.mark_processed("/new_video.mp4", status="completed")

        # Cleanup entries older than 0 days (all entries)
        deleted = tracker.cleanup_old_entries(days=0)

        assert deleted >= 2
        assert not tracker.is_processed("/old_video.mp4")
        assert not tracker.is_processed("/new_video.mp4")

    def test_get_statistics(self, tracker):
        """Test getting processing statistics."""
        # Add test data
        tracker.mark_processed("/video1.mp4", status="completed")
        tracker.mark_processed("/video2.mp4", status="completed")
        tracker.mark_processed("/video3.mp4", status="failed")

        stats = tracker.get_statistics()

        assert stats["total"] == 3
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_concurrent_access(self, temp_db_path):
        """Test concurrent access to the same database."""
        tracker1 = ProcessingTracker(temp_db_path)
        tracker2 = ProcessingTracker(temp_db_path)

        # Both should be able to write
        tracker1.mark_processed("/video1.mp4", status="completed")
        tracker2.mark_processed("/video2.mp4", status="completed")

        # Both should see each other's changes
        assert tracker1.is_processed("/video2.mp4")
        assert tracker2.is_processed("/video1.mp4")

        tracker1.close()
        tracker2.close()

    def test_invalid_status(self, tracker):
        """Test marking with invalid status."""
        with pytest.raises(ValueError):
            tracker.mark_processed("/video.mp4", status="invalid_status")
