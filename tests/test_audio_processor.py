import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from pydub import AudioSegment

from dnd_notetaker.audio_processor import AudioProcessor


class TestAudioProcessor:
    def setup_method(self):
        self.processor = AudioProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        self.processor.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        assert self.processor.MAX_CHUNK_SIZE == 24 * 1024 * 1024
        assert self.processor.temp_dirs == []
        assert hasattr(self.processor, "logger")

    def test_create_temp_dir(self):
        temp_dir = self.processor.create_temp_dir()

        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)
        assert temp_dir in self.processor.temp_dirs
        assert temp_dir.startswith(tempfile.gettempdir())
        assert "audio_processor_" in temp_dir

    def test_cleanup_removes_temp_dirs(self):
        # Create some temp directories
        temp_dir1 = self.processor.create_temp_dir()
        temp_dir2 = self.processor.create_temp_dir()

        # Verify they exist
        assert os.path.exists(temp_dir1)
        assert os.path.exists(temp_dir2)

        # Cleanup
        self.processor.cleanup()

        # Verify they're removed
        assert not os.path.exists(temp_dir1)
        assert not os.path.exists(temp_dir2)

    def test_cleanup_handles_missing_dirs(self):
        # Add a non-existent directory
        self.processor.temp_dirs.append("/non/existent/path")

        # Should not raise exception
        self.processor.cleanup()

    def test_verify_audio_file_valid(self):
        # Create a temporary file
        test_file = os.path.join(self.temp_dir, "test.mp3")
        with open(test_file, "w") as f:
            f.write("test")

        # Should not raise exception
        self.processor.verify_audio_file(test_file)

    def test_verify_audio_file_not_exists(self):
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            self.processor.verify_audio_file("/non/existent/file.mp3")

    def test_verify_audio_file_is_directory(self):
        with pytest.raises(ValueError, match="Path is not a file"):
            self.processor.verify_audio_file(self.temp_dir)

    @patch("dnd_notetaker.audio_processor.VideoFileClip")
    @patch("os.path.exists", return_value=True)
    def test_extract_audio_success(self, mock_exists, mock_video_clip):
        # Setup mocks
        mock_video = MagicMock()
        mock_video.duration = 100
        mock_audio = MagicMock()
        mock_video.audio = mock_audio
        mock_video_clip.return_value = mock_video

        # Call extract_audio
        video_path = "test_video.mp4"
        output_path = self.processor.extract_audio(video_path, self.temp_dir)

        # Verify
        assert output_path == os.path.join(self.temp_dir, "session_audio.mp3")
        mock_video_clip.assert_called_once_with(video_path)
        mock_audio.write_audiofile.assert_called_once()
        mock_video.close.assert_called_once()

    @patch("dnd_notetaker.audio_processor.VideoFileClip")
    def test_extract_audio_file_not_found(self, mock_video_clip):
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            self.processor.extract_audio("/non/existent/video.mp4", self.temp_dir)

    @patch("dnd_notetaker.audio_processor.VideoFileClip")
    @patch("os.path.exists", return_value=True)
    def test_extract_audio_handles_exception(self, mock_exists, mock_video_clip):
        mock_video_clip.side_effect = Exception("Video processing error")

        with pytest.raises(Exception, match="Video processing error"):
            self.processor.extract_audio("test_video.mp4", self.temp_dir)

    @patch("os.path.getsize", return_value=1024)  # 1KB file
    def test_split_audio_small_file(self, mock_getsize):
        # Create a test file
        test_file = os.path.join(self.temp_dir, "small_audio.mp3")
        with open(test_file, "w") as f:
            f.write("test")

        result = self.processor.split_audio(test_file, self.temp_dir)

        assert result == [test_file]
        assert len(self.processor.temp_dirs) == 0  # No temp dir created for small files

    @patch("subprocess.run")
    @patch(
        "dnd_notetaker.audio_processor.AudioProcessor.get_audio_duration",
        return_value=1800,
    )  # 30 minutes
    @patch("os.path.getsize", return_value=50 * 1024 * 1024)  # 50MB
    def test_split_audio_large_file(self, mock_getsize, mock_duration, mock_subprocess):
        # Mock successful ffmpeg execution
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Create test file
        test_file = os.path.join(self.temp_dir, "large_audio.mp3")
        with open(test_file, "w") as f:
            f.write("test")

        # Mock os.path.exists for chunk files
        with patch("os.path.exists") as mock_exists:

            def exists_side_effect(path):
                if path == test_file or "chunk_" in path:
                    return True
                return False

            mock_exists.side_effect = exists_side_effect

            # Mock chunk file sizes
            with patch("os.path.getsize") as mock_size:

                def getsize_side_effect(path):
                    if path == test_file:
                        return 50 * 1024 * 1024
                    elif "chunk_" in path:
                        return 10 * 1024 * 1024  # 10MB chunks
                    return 0

                mock_size.side_effect = getsize_side_effect

                result = self.processor.split_audio(test_file, self.temp_dir)

        # Should split into 2 chunks (30 minutes / 15 minutes per chunk)
        assert len(result) == 2
        assert all("chunk_" in path for path in result)
        assert mock_subprocess.call_count == 2  # Two ffmpeg calls

    def test_split_audio_invalid_file(self):
        with pytest.raises(FileNotFoundError):
            self.processor.split_audio("/non/existent/audio.mp3", self.temp_dir)

    @patch("subprocess.run")
    @patch(
        "dnd_notetaker.audio_processor.AudioProcessor.get_audio_duration",
        return_value=1800,
    )  # 30 minutes
    @patch("os.path.getsize", return_value=50 * 1024 * 1024)
    def test_split_audio_handles_processing_error(
        self, mock_getsize, mock_duration, mock_subprocess
    ):
        # Mock ffmpeg failure
        mock_subprocess.return_value = MagicMock(
            returncode=1, stdout="", stderr="ffmpeg error"
        )

        test_file = os.path.join(self.temp_dir, "error_audio.mp3")
        with open(test_file, "w") as f:
            f.write("test")

        with pytest.raises(Exception, match="ffmpeg failed"):
            self.processor.split_audio(test_file, self.temp_dir)

        # Verify cleanup was attempted
        assert len(self.processor.temp_dirs) > 0
