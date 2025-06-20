"""Integration tests for dry-run functionality"""

import pytest
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import json


class TestDryRunIntegration:
    """Test complete pipeline in dry-run mode"""
    
    def test_full_pipeline_dry_run(self, tmp_path, capsys):
        """Test complete pipeline in dry-run mode"""
        # Create a minimal config file
        config_file = tmp_path / "config.json"
        config_data = {
            "openai_api_key": "",
            "google_service_account": str(tmp_path / "service_account.json"),
            "output_dir": str(tmp_path / "output")
        }
        config_file.write_text(json.dumps(config_data))
        
        # Run with dry-run flag
        result = subprocess.run([
            sys.executable, "-m", "dnd_notetaker", 
            "TEST_FILE_ID", "--dry-run",
            "--config", str(config_file),
            "--output-dir", str(tmp_path / "output")
        ], capture_output=True, text=True)
        
        # Should complete successfully
        assert result.returncode == 0
        
        # Verify output contains all expected dry-run messages
        output = result.stdout
        assert "[DRY RUN] Would download from Google Drive:" in output
        assert "[DRY RUN] Would extract audio using FFmpeg:" in output
        assert "[DRY RUN] Would transcribe audio using OpenAI Whisper:" in output
        assert "[DRY RUN] Would generate notes using OpenAI GPT:" in output
        assert "[DRY RUN] Would save artifacts to:" in output
        
        # Verify no files were created in output directory
        output_dir = tmp_path / "output"
        if output_dir.exists():
            assert len(list(output_dir.iterdir())) == 0
        
        # Verify no external calls were made (no credentials needed)
        assert "Error" not in output
        assert "Exception" not in output
    
    def test_dry_run_no_file_id(self, tmp_path):
        """Test dry-run without file ID"""
        # Create a minimal config file
        config_file = tmp_path / "config.json"
        config_data = {
            "openai_api_key": "",
            "google_service_account": str(tmp_path / "service_account.json"),
            "output_dir": str(tmp_path / "output")
        }
        config_file.write_text(json.dumps(config_data))
        
        # Run without file ID
        result = subprocess.run([
            sys.executable, "-m", "dnd_notetaker", 
            "--dry-run",
            "--config", str(config_file)
        ], capture_output=True, text=True)
        
        # Should complete successfully
        assert result.returncode == 0
        
        # Should show search for most recent
        assert "[DRY RUN] Would search for most recent" in result.stdout
    
    def test_dry_run_no_credentials(self):
        """Test dry-run without any credentials"""
        # Run with non-existent config
        result = subprocess.run([
            sys.executable, "-m", "dnd_notetaker",
            "TEST_FILE_ID", "--dry-run"
        ], capture_output=True, text=True, env={})
        
        # Should complete successfully without errors
        assert result.returncode == 0
        assert "[DRY RUN]" in result.stdout
    
    def test_dry_run_custom_output_dir(self, tmp_path):
        """Test dry-run with custom output directory"""
        custom_dir = tmp_path / "custom_output"
        
        result = subprocess.run([
            sys.executable, "-m", "dnd_notetaker",
            "TEST_FILE_ID", "--dry-run",
            "--output-dir", str(custom_dir)
        ], capture_output=True, text=True)
        
        # Should complete successfully
        assert result.returncode == 0
        
        # Should show custom directory in output
        assert str(custom_dir) in result.stdout
        
        # Directory should not be created
        assert not custom_dir.exists()
    
    def test_dry_run_component_interactions(self):
        """Test that all components receive dry_run config"""
        from dnd_notetaker.meet_notes import main
        from dnd_notetaker.config import Config
        
        with patch('dnd_notetaker.meet_notes.MeetProcessor') as mock_processor_class:
            # Mock the processor
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Run with dry-run
            test_args = ['dnd_notetaker', 'FILE_ID', '--dry-run']
            with patch.object(sys, 'argv', test_args):
                with patch('dnd_notetaker.meet_notes.Config') as mock_config_class:
                    mock_config = Mock()
                    mock_config.dry_run = True
                    mock_config.output_dir = Path("/tmp/output")
                    mock_config_class.return_value = mock_config
                    
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    # Verify config was created with dry_run=True
                    mock_config_class.assert_called_with(config_path=None, dry_run=True)
                    
                    # Verify processor was created with the config
                    assert mock_processor_class.called
                    args, kwargs = mock_processor_class.call_args
                    assert args[0] == mock_config  # First arg should be config