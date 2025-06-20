"""Tests for the simplified configuration management"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from dnd_notetaker.config import Config


class TestConfig:
    """Test configuration management"""
    
    def test_load_existing_config(self):
        """Test loading existing configuration file"""
        config_data = {
            "openai_api_key": "test-key",
            "google_service_account": "/path/to/service.json",
            "output_dir": "/path/to/output"
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
                config = Config()
                
                assert config._config == config_data
    
    def test_create_default_config(self):
        """Test creation of default config when none exists"""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()) as m:
                    with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
                        config = Config()
                        
                        # Check default values
                        assert config._config['openai_api_key'] == 'env-key'
                        assert 'service_account.json' in config._config['google_service_account']
                        assert 'meet_notes_output' in config._config['output_dir']
                        
                        # Check file was written
                        m.assert_called()
    
    def test_openai_api_key_property(self):
        """Test OpenAI API key property"""
        config = Config()
        config._config = {"openai_api_key": "test-key"}
        
        assert config.openai_api_key == "test-key"
    
    def test_openai_api_key_missing_raises_error(self):
        """Test error when OpenAI key is missing"""
        config = Config()
        config._config = {"openai_api_key": ""}
        
        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            _ = config.openai_api_key
    
    def test_service_account_path_property(self):
        """Test service account path property"""
        with tempfile.NamedTemporaryFile() as tf:
            config = Config()
            config._config = {"google_service_account": tf.name}
            
            assert config.service_account_path == Path(tf.name)
    
    def test_service_account_path_missing_raises_error(self):
        """Test error when service account file doesn't exist"""
        config = Config()
        config._config = {"google_service_account": "/nonexistent/path.json"}
        
        with pytest.raises(ValueError, match="Service account file not found"):
            _ = config.service_account_path
    
    def test_output_dir_property(self):
        """Test output directory property"""
        with tempfile.TemporaryDirectory() as td:
            config = Config()
            config._config = {"output_dir": td}
            
            output_dir = config.output_dir
            assert output_dir == Path(td)
            assert output_dir.exists()
    
    def test_output_dir_creates_if_missing(self):
        """Test output directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as td:
            new_dir = Path(td) / "new_output"
            config = Config()
            config._config = {"output_dir": str(new_dir)}
            
            output_dir = config.output_dir
            assert output_dir.exists()
            assert output_dir == new_dir
    
    def test_dry_run_flag(self):
        """Test that Config properly stores dry_run flag"""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()):
                    config = Config(dry_run=True)
                    assert config.dry_run is True
                    
                    config = Config(dry_run=False)
                    assert config.dry_run is False
    
    def test_dry_run_no_config_creation(self):
        """Test that dry_run mode doesn't create config files"""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                with patch('builtins.open', mock_open()) as mock_file:
                    config = Config(dry_run=True)
                    
                    # Should not create directories or files in dry run
                    mock_mkdir.assert_not_called()
                    mock_file.assert_not_called()
    
    def test_dry_run_no_validation_errors(self):
        """Test that dry_run mode bypasses validation errors"""
        config = Config(dry_run=True)
        config._config = {"openai_api_key": "", "google_service_account": "/nonexistent"}
        
        # Should not raise errors in dry run mode
        assert config.openai_api_key == ""
        assert config.service_account_path == Path("/nonexistent")
    
    def test_dry_run_no_output_dir_creation(self):
        """Test that dry_run mode doesn't create output directory"""
        with tempfile.TemporaryDirectory() as td:
            new_dir = Path(td) / "should_not_exist"
            config = Config(dry_run=True)
            config._config = {"output_dir": str(new_dir)}
            
            output_dir = config.output_dir
            assert not new_dir.exists()  # Directory should not be created
            assert output_dir == new_dir