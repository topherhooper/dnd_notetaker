"""Tests for the MeetProcessor orchestrator"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile

from dnd_notetaker.meet_processor import MeetProcessor


class TestMeetProcessor:
    """Test the main processing orchestrator"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        config = Mock()
        config.service_account_path = Path("/path/to/service.json")
        config.openai_api_key = "test-key"
        config.dry_run = False
        return config
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    def test_init(self, mock_artifacts, mock_notes, mock_trans, mock_audio, mock_drive, 
                  mock_config, temp_output_dir):
        """Test processor initialization"""
        processor = MeetProcessor(mock_config, temp_output_dir)
        
        # Verify components were initialized
        mock_drive.assert_called_once_with(mock_config.service_account_path, mock_config)
        mock_audio.assert_called_once_with(mock_config)
        mock_trans.assert_called_once_with(mock_config.openai_api_key, mock_config)
        mock_notes.assert_called_once_with(mock_config.openai_api_key, mock_config)
        mock_artifacts.assert_called_once_with(temp_output_dir, mock_config)
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    @patch('dnd_notetaker.meet_processor.tqdm')
    def test_process_full_pipeline(self, mock_tqdm, mock_artifacts_class, mock_notes_class, 
                                  mock_trans_class, mock_audio_class, mock_drive_class,
                                  mock_config, temp_output_dir):
        """Test full processing pipeline"""
        # Create test files
        video_path = temp_output_dir / "test.mp4"
        video_path.write_text("video")
        
        # Setup mocks
        processor = MeetProcessor(mock_config, temp_output_dir)
        processor.drive_handler = Mock()
        processor.audio_extractor = Mock()
        processor.transcriber = Mock()
        processor.note_generator = Mock()
        processor.artifacts = Mock()
        
        # Configure mock returns
        processor.drive_handler.download_most_recent.return_value = video_path
        processor.transcriber.transcribe.return_value = "Test transcript"
        processor.note_generator.generate.return_value = "Test notes"
        processor.artifacts.create_share_bundle.return_value = "http://share.url"
        
        # Run process
        processor.process()
        
        # Verify pipeline execution
        processor.drive_handler.download_most_recent.assert_called_once()
        processor.audio_extractor.extract.assert_called_once()
        processor.transcriber.transcribe.assert_called_once()
        processor.note_generator.generate.assert_called_once_with("Test transcript")
        processor.artifacts.create_share_bundle.assert_called_once()
        
        # Verify files were created
        assert (temp_output_dir / "meeting.mp4").exists()
        assert (temp_output_dir / "transcript.txt").exists()
        assert (temp_output_dir / "notes.txt").exists()
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    @patch('dnd_notetaker.meet_processor.tqdm')
    def test_process_with_file_id(self, mock_tqdm, mock_artifacts_class, mock_notes_class, 
                                 mock_trans_class, mock_audio_class, mock_drive_class,
                                 mock_config, temp_output_dir):
        """Test processing with specific file ID"""
        # Create test files
        video_path = temp_output_dir / "test.mp4"
        video_path.write_text("video")
        
        # Setup mocks
        processor = MeetProcessor(mock_config, temp_output_dir)
        processor.drive_handler = Mock()
        processor.audio_extractor = Mock()
        processor.transcriber = Mock()
        processor.note_generator = Mock()
        processor.artifacts = Mock()
        
        # Configure mock returns
        processor.drive_handler.download_file.return_value = video_path
        processor.transcriber.transcribe.return_value = "Test transcript"
        processor.note_generator.generate.return_value = "Test notes"
        processor.artifacts.create_share_bundle.return_value = "http://share.url"
        
        # Run process with file ID
        test_file_id = "abc123"
        processor.process(test_file_id)
        
        # Verify download_file was called instead of download_most_recent
        processor.drive_handler.download_file.assert_called_once_with(test_file_id, temp_output_dir)
        processor.drive_handler.download_most_recent.assert_not_called()
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    @patch('dnd_notetaker.meet_processor.tqdm')
    def test_checkpointing_skips_existing_audio(self, mock_tqdm, mock_artifacts_class, mock_notes_class, 
                                               mock_trans_class, mock_audio_class, mock_drive_class,
                                               mock_config, temp_output_dir):
        """Test that existing audio file is not re-extracted"""
        # Create existing audio file
        audio_path = temp_output_dir / "audio.mp3"
        audio_path.write_text("existing audio")
        
        # Create video file
        video_path = temp_output_dir / "meeting.mp4"
        video_path.write_text("video")
        
        # Setup processor
        processor = MeetProcessor(mock_config, temp_output_dir)
        processor.drive_handler = Mock()
        processor.audio_extractor = Mock()
        processor.transcriber = Mock()
        processor.note_generator = Mock()
        processor.artifacts = Mock()
        
        processor.drive_handler.download_most_recent.return_value = video_path
        processor.transcriber.transcribe.return_value = "Test transcript"
        processor.note_generator.generate.return_value = "Test notes"
        processor.artifacts.create_share_bundle.return_value = "http://share.url"
        
        # Run process
        processor.process()
        
        # Verify audio extraction was skipped
        processor.audio_extractor.extract.assert_not_called()
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    @patch('dnd_notetaker.meet_processor.tqdm')
    def test_checkpointing_skips_existing_transcript(self, mock_tqdm, mock_artifacts_class, mock_notes_class, 
                                                    mock_trans_class, mock_audio_class, mock_drive_class,
                                                    mock_config, temp_output_dir):
        """Test that existing transcript is not re-generated"""
        # Create existing files
        audio_path = temp_output_dir / "audio.mp3"
        audio_path.write_text("audio")
        transcript_path = temp_output_dir / "transcript.txt"
        transcript_path.write_text("existing transcript")
        video_path = temp_output_dir / "meeting.mp4"
        video_path.write_text("video")
        
        # Setup processor
        processor = MeetProcessor(mock_config, temp_output_dir)
        processor.drive_handler = Mock()
        processor.audio_extractor = Mock()
        processor.transcriber = Mock()
        processor.note_generator = Mock()
        processor.artifacts = Mock()
        
        processor.drive_handler.download_most_recent.return_value = video_path
        processor.note_generator.generate.return_value = "Test notes"
        processor.artifacts.create_share_bundle.return_value = "http://share.url"
        
        # Run process
        processor.process()
        
        # Verify transcription was skipped
        processor.transcriber.transcribe.assert_not_called()
        
        # Verify note generation used existing transcript
        processor.note_generator.generate.assert_called_once_with("existing transcript")
    
    @patch('dnd_notetaker.meet_processor.SimplifiedDriveHandler')
    @patch('dnd_notetaker.meet_processor.AudioExtractor')
    @patch('dnd_notetaker.meet_processor.Transcriber')
    @patch('dnd_notetaker.meet_processor.NoteGenerator')
    @patch('dnd_notetaker.meet_processor.Artifacts')
    @patch('dnd_notetaker.meet_processor.tqdm')
    def test_notes_always_regenerated(self, mock_tqdm, mock_artifacts_class, mock_notes_class, 
                                     mock_trans_class, mock_audio_class, mock_drive_class,
                                     mock_config, temp_output_dir):
        """Test that notes are always regenerated even if they exist"""
        # Create all existing files
        audio_path = temp_output_dir / "audio.mp3"
        audio_path.write_text("audio")
        transcript_path = temp_output_dir / "transcript.txt"
        transcript_path.write_text("transcript")
        notes_path = temp_output_dir / "notes.txt"
        notes_path.write_text("old notes")
        video_path = temp_output_dir / "meeting.mp4"
        video_path.write_text("video")
        
        # Setup processor
        processor = MeetProcessor(mock_config, temp_output_dir)
        processor.drive_handler = Mock()
        processor.audio_extractor = Mock()
        processor.transcriber = Mock()
        processor.note_generator = Mock()
        processor.artifacts = Mock()
        
        processor.drive_handler.download_most_recent.return_value = video_path
        processor.note_generator.generate.return_value = "New notes"
        processor.artifacts.create_share_bundle.return_value = "http://share.url"
        
        # Run process
        processor.process()
        
        # Verify notes were regenerated
        processor.note_generator.generate.assert_called_once_with("transcript")
        
        # Verify new notes were written
        assert notes_path.read_text() == "New notes"