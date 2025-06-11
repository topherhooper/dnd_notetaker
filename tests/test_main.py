import argparse
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dnd_notetaker.main import MeetingProcessor, main


def patch_all_processors(func):
    """Helper decorator to patch all processors"""
    return patch("dnd_notetaker.main.DocsUploader")(
        patch("dnd_notetaker.main.TranscriptProcessor")(
            patch("dnd_notetaker.main.Transcriber")(
                patch("dnd_notetaker.main.AudioProcessor")(
                    patch("dnd_notetaker.main.DriveHandler")(func)
                )
            )
        )
    )


class TestMeetingProcessor:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config = {
            "openai_api_key": "test_api_key",
        }

        # Write test config
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_init_success(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        processor = MeetingProcessor(self.config_path)

        assert processor.config == self.config
        mock_drive.assert_called_once()
        mock_audio.assert_called_once()
        mock_transcriber.assert_called_once_with(self.config["openai_api_key"])
        mock_processor.assert_called_once_with(self.config["openai_api_key"])
        mock_uploader.assert_called_once()

    def test_init_missing_config(self):
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            MeetingProcessor("/non/existent/config.json")

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_init_invalid_config(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        # Write invalid JSON
        with open(self.config_path, "w") as f:
            f.write("invalid json")

        with pytest.raises(json.JSONDecodeError):
            MeetingProcessor(self.config_path)

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_verify_output_directory(
        self, mock_email, mock_audio, mock_transcriber, mock_processor, mock_uploader
    ):
        processor = MeetingProcessor(self.config_path)

        test_dir = os.path.join(self.temp_dir, "test_output")
        result = processor.verify_output_directory(test_dir)

        assert result is True
        assert os.path.exists(test_dir)

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_get_output_dir_from_filename(
        self, mock_drive_handler, mock_audio, mock_transcriber, mock_processor, mock_uploader
    ):
        processor = MeetingProcessor(self.config_path)

        # Test standard filename format
        filename = "DnD - 2025-01-10 18-41 CST - Recording"
        result = processor.get_output_dir_from_filename(filename)
        assert result == os.path.join("output", "dnd_sessions_2025_01_10")

        # Test different meeting name
        filename = "Weekly Meeting - 2025-02-15 10-30 EST - Recording"
        result = processor.get_output_dir_from_filename(filename)
        assert result == os.path.join("output", "weekly_meeting_sessions_2025_02_15")

        # Test malformed filename
        filename = "InvalidFilename"
        result = processor.get_output_dir_from_filename(filename)
        assert result == os.path.join("output", "session_default")

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    @patch("dnd_notetaker.main.tqdm")
    @patch("os.rename")
    @patch("shutil.rmtree")
    def test_process_meeting_success(
        self,
        mock_rmtree,
        mock_rename,
        mock_tqdm,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        # Setup mocks
        processor = MeetingProcessor(self.config_path)

        # Mock drive handler
        mock_drive_instance = mock_drive.return_value
        mock_drive_instance.download_recording.return_value = (
            "/tmp/temp_download/DnD - 2025-01-10 18-41 CST - Recording.mp4"
        )

        # Mock audio processor
        mock_audio_instance = mock_audio.return_value
        mock_audio_instance.extract_audio.return_value = "/tmp/audio.mp3"

        # Mock transcriber
        mock_transcriber_instance = mock_transcriber.return_value
        mock_transcriber_instance.get_transcript.return_value = (
            "transcript text",
            "/output/transcript.txt",
        )

        # Mock transcript processor
        mock_processor_instance = mock_processor.return_value
        mock_processor_instance.process_transcript.return_value = (
            "processed notes",
            "/output/notes.txt",
        )

        # Mock docs uploader
        mock_uploader_instance = mock_uploader.return_value
        mock_uploader_instance.upload_notes.return_value = (
            "https://docs.google.com/document/d/123"
        )

        # Mock progress bar
        mock_pbar = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = mock_pbar

        # Run process_meeting
        result = processor.process_meeting(
            name_filter="DnD Meeting", output_dir=None, keep_temp_files=False
        )

        # Verify results
        assert result["doc_url"] == "https://docs.google.com/document/d/123"
        assert "video_path" in result
        assert "transcript_path" in result
        assert "notes_path" in result
        assert "timestamp" in result

        # Verify method calls
        mock_drive_instance.download_recording.assert_called_once()
        mock_audio_instance.extract_audio.assert_called_once()
        mock_transcriber_instance.get_transcript.assert_called_once()
        mock_processor_instance.process_transcript.assert_called_once()
        mock_uploader_instance.upload_notes.assert_called_once()

        # Verify cleanup
        mock_audio_instance.cleanup.assert_called_once()

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_process_meeting_download_error(
        self, mock_drive, mock_audio, mock_transcriber, mock_processor, mock_uploader
    ):
        processor = MeetingProcessor(self.config_path)

        # Mock drive handler to raise error
        mock_drive_instance = mock_drive.return_value
        mock_drive_instance.download_recording.side_effect = Exception(
            "Download failed"
        )

        # Run process_meeting and expect error
        with pytest.raises(Exception, match="Download failed"):
            processor.process_meeting(name_filter="DnD Meeting")


class TestMainFunction:
    @patch("sys.argv", ["main.py", "process", "--name", "Test Meeting"])
    @patch("dnd_notetaker.main.MeetingProcessor")
    def test_main_process_command(self, mock_processor_class):
        # Mock processor instance
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_meeting.return_value = {
            "video_path": "/output/video.mp4",
            "transcript_path": "/output/transcript.txt",
            "notes_path": "/output/notes.txt",
            "doc_url": "https://docs.google.com/document/d/123",
            "timestamp": "20250110",
        }

        # Run main
        with patch("builtins.print"):
            main()

        # Verify processor was created and called
        mock_processor_class.assert_called_once_with()
        mock_processor.process_meeting.assert_called_once_with(
            name_filter="Test Meeting",
            file_id=None,
            output_dir=None,
            keep_temp_files=False,
            existing_dir=None,
        )

    @patch("sys.argv", ["main.py", "clean", "--age", "48"])
    @patch("dnd_notetaker.main.cleanup_old_temp_directories")
    def test_main_clean_command(self, mock_cleanup):
        mock_cleanup.return_value = (5, ["dir1", "dir2"])

        # Run main
        with patch("builtins.print") as mock_print:
            main()

        # Verify cleanup was called
        mock_cleanup.assert_called_once_with("meeting_outputs", 48)

        # Verify output
        mock_print.assert_any_call("\nCleaned up 5 temporary directories")
        mock_print.assert_any_call("2 directories remain")

    @patch("sys.argv", ["main.py", "list"])
    @patch("dnd_notetaker.main.list_temp_directories")
    def test_main_list_command(self, mock_list):
        mock_list.return_value = [
            {
                "path": "/tmp/meeting_processor_123",
                "created": "2025-01-10 10:00:00",
                "age_hours": 2.5,
                "size_mb": 150.5,
            }
        ]

        # Run main
        with patch("builtins.print") as mock_print:
            main()

        # Verify list was called
        mock_list.assert_called_once_with("meeting_outputs")

        # Verify output
        mock_print.assert_any_call("\nTemporary Directories:")
        mock_print.assert_any_call("\nPath: /tmp/meeting_processor_123")

    @patch("sys.argv", ["main.py"])
    def test_main_no_command(self):
        # Run main with no command
        with patch("builtins.print"):
            main()

        # Should print help (not crash)

    @patch("sys.argv", ["main.py", "process"])
    @patch("dnd_notetaker.main.MeetingProcessor")
    def test_main_process_error(self, mock_processor_class):
        # Mock processor to raise error
        mock_processor_class.side_effect = Exception("Processing failed")

        # Run main and expect error
        with pytest.raises(Exception, match="Processing failed"):
            main()


class TestIntegrationScenarios:
    """Test complete scenarios with minimal mocking"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")

        # Create test config
        self.config = {
            "openai_api_key": "test_api_key",
        }

        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_custom_output_directory(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        """Test processing with custom output directory"""
        processor = MeetingProcessor(self.config_path)

        # Setup minimal mocks
        mock_drive.return_value.download_recording.return_value = os.path.join(
            self.temp_dir, "video.mp4"
        )
        mock_audio.return_value.extract_audio.return_value = os.path.join(
            self.temp_dir, "audio.mp3"
        )
        mock_transcriber.return_value.get_transcript.return_value = (
            "text",
            os.path.join(self.temp_dir, "transcript.txt"),
        )
        mock_processor.return_value.process_transcript.return_value = (
            "notes",
            os.path.join(self.temp_dir, "notes.txt"),
        )
        mock_uploader.return_value.upload_notes.return_value = (
            "https://docs.google.com/doc"
        )

        # Create test video file
        with open(os.path.join(self.temp_dir, "video.mp4"), "w") as f:
            f.write("fake video")
        # Create test transcript file
        with open(os.path.join(self.temp_dir, "transcript.txt"), "w") as f:
            f.write("fake transcript")

        # Custom output directory
        custom_output = os.path.join(self.temp_dir, "custom_output")

        # Process with custom directory
        result = processor.process_meeting(
            name_filter="Test", output_dir=custom_output, keep_temp_files=True
        )

        # Verify custom directory was created
        assert os.path.exists(custom_output)

    def test_output_directory_permissions(self):
        """Test handling of read-only output directory"""
        # This test would require OS-level permission manipulation
        # Skipping for now as it's platform-dependent
        pass

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_find_existing_files_with_transcript(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        """Test finding existing files including transcript"""
        processor = MeetingProcessor(self.config_path)

        # Create test directory with files
        test_dir = os.path.join(self.temp_dir, "test_session")
        os.makedirs(test_dir, exist_ok=True)

        # Create test files
        video_path = os.path.join(test_dir, "recording.mp4")
        audio_path = os.path.join(test_dir, "session_audio.mp3")
        transcript_path = os.path.join(test_dir, "full_transcript_20240101_120000.txt")

        with open(video_path, "w") as f:
            f.write("video")
        with open(audio_path, "w") as f:
            f.write("audio")
        with open(transcript_path, "w") as f:
            f.write("transcript")

        # Test finding files
        found_video, found_audio, found_transcript = processor.find_existing_files(
            test_dir
        )

        assert found_video == video_path
        assert found_audio == audio_path
        assert found_transcript == transcript_path

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_find_existing_files_multiple_transcripts(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        """Test finding most recent transcript when multiple exist"""
        processor = MeetingProcessor(self.config_path)

        # Create test directory with files
        test_dir = os.path.join(self.temp_dir, "test_session")
        os.makedirs(test_dir, exist_ok=True)

        # Create multiple transcript files
        transcript1 = os.path.join(test_dir, "full_transcript_20240101_120000.txt")
        transcript2 = os.path.join(test_dir, "full_transcript_20240101_130000.txt")

        with open(transcript1, "w") as f:
            f.write("old transcript")

        # Wait a tiny bit to ensure different mtime
        import time

        time.sleep(0.01)

        with open(transcript2, "w") as f:
            f.write("new transcript")

        # Test finding files
        _, _, found_transcript = processor.find_existing_files(test_dir)

        # Should find the most recent transcript
        assert found_transcript == transcript2

    @patch("dnd_notetaker.main.DocsUploader")
    @patch("dnd_notetaker.main.TranscriptProcessor")
    @patch("dnd_notetaker.main.Transcriber")
    @patch("dnd_notetaker.main.AudioProcessor")
    @patch("dnd_notetaker.main.DriveHandler")
    def test_process_with_existing_transcript(
        self,
        mock_drive,
        mock_audio,
        mock_transcriber,
        mock_processor,
        mock_uploader,
    ):
        """Test process flow when transcript already exists"""
        processor = MeetingProcessor(self.config_path)

        # Create test directory with existing files
        test_dir = os.path.join(self.temp_dir, "existing_session")
        os.makedirs(test_dir, exist_ok=True)

        # Create existing video, audio, and transcript
        video_path = os.path.join(test_dir, "recording.mp4")
        audio_path = os.path.join(test_dir, "session_audio.mp3")
        transcript_path = os.path.join(test_dir, "full_transcript_20240101_120000.txt")

        with open(video_path, "w") as f:
            f.write("video")
        with open(audio_path, "w") as f:
            f.write("audio")
        with open(transcript_path, "w") as f:
            f.write("existing transcript content")

        # Configure mocks
        mock_processor.return_value.process_transcript.return_value = (
            "notes",
            os.path.join(test_dir, "notes.txt"),
        )
        mock_uploader.return_value.upload_notes.return_value = (
            "https://docs.google.com/doc"
        )

        # Process with existing directory
        result = processor.process_meeting(name_filter="Test", existing_dir=test_dir)

        # Verify transcript generation was NOT called
        mock_transcriber.return_value.get_transcript.assert_not_called()

        # Verify processor was called with existing transcript
        mock_processor.return_value.process_transcript.assert_called_once()
        call_args = mock_processor.return_value.process_transcript.call_args[0]
        assert call_args[0] == transcript_path
