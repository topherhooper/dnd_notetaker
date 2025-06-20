"""Tests for the simplified meet_notes entry point"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

from dnd_notetaker.meet_notes import main


class TestMeetNotes:
    """Test the main entry point"""
    
    @patch('dnd_notetaker.meet_notes.Config')
    @patch('dnd_notetaker.meet_notes.MeetProcessor')
    def test_main_no_args(self, mock_processor_class, mock_config_class):
        """Test processing with no arguments (most recent recording)"""
        # Setup mocks
        mock_config = Mock()
        mock_config.output_dir = Path('/tmp/output')
        mock_config_class.return_value = mock_config
        
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        
        # Mock sys.argv
        with patch.object(sys, 'argv', ['meet_notes']):
            # Run main
            main()
        
        # Verify
        mock_config_class.assert_called_once()
        mock_processor_class.assert_called_once()
        mock_processor.process.assert_called_once_with(None)
    
    @patch('dnd_notetaker.meet_notes.Config')
    @patch('dnd_notetaker.meet_notes.MeetProcessor')
    def test_main_with_file_id(self, mock_processor_class, mock_config_class):
        """Test processing with specific file ID"""
        # Setup mocks
        mock_config = Mock()
        mock_config.output_dir = Path('/tmp/output')
        mock_config_class.return_value = mock_config
        
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        
        # Mock sys.argv with file ID
        test_file_id = "abc123"
        with patch.object(sys, 'argv', ['meet_notes', test_file_id]):
            # Run main
            main()
        
        # Verify
        mock_processor.process.assert_called_once_with(test_file_id)
    
    @patch('dnd_notetaker.meet_notes.Config')
    @patch('dnd_notetaker.meet_notes.MeetProcessor')
    def test_main_handles_keyboard_interrupt(self, mock_processor_class, mock_config_class):
        """Test graceful handling of keyboard interrupt"""
        # Setup mocks
        mock_config = Mock()
        mock_config.output_dir = Path('/tmp/output')
        mock_config_class.return_value = mock_config
        
        mock_processor = Mock()
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor
        
        # Run main and expect exit
        with patch.object(sys, 'argv', ['meet_notes']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 1
    
    @patch('dnd_notetaker.meet_notes.Config')
    @patch('dnd_notetaker.meet_notes.MeetProcessor')
    def test_main_handles_errors(self, mock_processor_class, mock_config_class):
        """Test handling of general errors"""
        # Setup mocks
        mock_config = Mock()
        mock_config.output_dir = Path('/tmp/output')
        mock_config_class.return_value = mock_config
        
        mock_processor = Mock()
        mock_processor.process.side_effect = RuntimeError("Test error")
        mock_processor_class.return_value = mock_processor
        
        # Run main and expect exit
        with patch.object(sys, 'argv', ['meet_notes']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 1