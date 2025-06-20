"""Tests for the artifacts management and sharing"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

from dnd_notetaker.artifacts import Artifacts


class TestArtifacts:
    """Test artifacts management functionality"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory with test files"""
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td)
            
            # Create test files
            (output_dir / "meeting.mp4").write_text("video content")
            (output_dir / "audio.mp3").write_text("audio content")
            (output_dir / "transcript.txt").write_text("transcript content")
            (output_dir / "notes.txt").write_text("notes content")
            
            yield output_dir
    
    @pytest.fixture
    def artifacts(self, temp_output_dir):
        """Create artifacts instance"""
        return Artifacts(temp_output_dir)
    
    def test_init(self, artifacts):
        """Test artifacts initialization"""
        assert 'created' in artifacts.metadata
        assert 'id' in artifacts.metadata
        assert len(artifacts.metadata['id']) == 8
        assert artifacts.metadata['files'] == {}
    
    def test_create_share_bundle(self, artifacts, temp_output_dir):
        """Test creating a shareable bundle"""
        # Create bundle
        share_url = artifacts.create_share_bundle(
            video_path=temp_output_dir / "meeting.mp4",
            audio_path=temp_output_dir / "audio.mp3",
            transcript_path=temp_output_dir / "transcript.txt",
            notes_path=temp_output_dir / "notes.txt"
        )
        
        # Verify URL format
        assert share_url.startswith("file://")
        assert "index.html" in share_url
        
        # Verify metadata was saved
        metadata_file = temp_output_dir / "artifacts.json"
        assert metadata_file.exists()
        
        # Load and verify metadata
        with open(metadata_file) as f:
            saved_metadata = json.load(f)
        
        assert saved_metadata['id'] == artifacts.metadata['id']
        assert 'video' in saved_metadata['files']
        assert 'audio' in saved_metadata['files']
        assert 'transcript' in saved_metadata['files']
        assert 'notes' in saved_metadata['files']
        
        # Verify HTML was created
        html_file = temp_output_dir / "index.html"
        assert html_file.exists()
    
    def test_file_metadata(self, artifacts, temp_output_dir):
        """Test file metadata recording"""
        artifacts.create_share_bundle(
            video_path=temp_output_dir / "meeting.mp4",
            audio_path=temp_output_dir / "audio.mp3",
            transcript_path=temp_output_dir / "transcript.txt",
            notes_path=temp_output_dir / "notes.txt"
        )
        
        # Check video metadata
        video_meta = artifacts.metadata['files']['video']
        assert video_meta['name'] == 'meeting.mp4'
        assert video_meta['size'] == '13.0 B'  # "video content"
        assert video_meta['path'] == 'meeting.mp4'
        
        # Check audio metadata
        audio_meta = artifacts.metadata['files']['audio']
        assert audio_meta['name'] == 'audio.mp3'
        assert audio_meta['size'] == '13.0 B'  # "audio content"
        assert audio_meta['path'] == 'audio.mp3'
    
    def test_get_file_size_formatting(self, artifacts):
        """Test file size formatting"""
        # Create files of different sizes
        test_cases = [
            (100, "100.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1536, "1.5 KB"),
            (1024 * 1024 * 1.5, "1.5 MB"),
        ]
        
        for size_bytes, expected in test_cases:
            # Create a mock path with specific size
            mock_path = Mock()
            mock_path.stat.return_value.st_size = size_bytes
            
            result = artifacts._get_file_size(mock_path)
            assert result == expected
    
    def test_html_viewer_content(self, artifacts, temp_output_dir):
        """Test HTML viewer generation"""
        artifacts.create_share_bundle(
            video_path=temp_output_dir / "meeting.mp4",
            audio_path=temp_output_dir / "audio.mp3",
            transcript_path=temp_output_dir / "transcript.txt",
            notes_path=temp_output_dir / "notes.txt"
        )
        
        # Read generated HTML
        html_file = temp_output_dir / "index.html"
        html_content = html_file.read_text()
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<title>Meeting Notes" in html_content
        assert artifacts.metadata['id'] in html_content
        
        # Verify all artifacts are referenced
        assert "audio.mp3" in html_content
        assert "transcript.txt" in html_content
        assert "notes.txt" in html_content
        assert "meeting.mp4" in html_content
        
        # Verify interactive elements
        assert '<audio controls' in html_content
        assert 'download>Download Transcript</a>' in html_content
        assert 'download>Download Audio</a>' in html_content
        assert 'download>Download Video</a>' in html_content
        
        # Verify JavaScript for loading notes
        assert "fetch('notes.txt')" in html_content
    
    def test_html_viewer_styling(self, artifacts, temp_output_dir):
        """Test HTML viewer has proper styling"""
        artifacts.create_share_bundle(
            video_path=temp_output_dir / "meeting.mp4",
            audio_path=temp_output_dir / "audio.mp3",
            transcript_path=temp_output_dir / "transcript.txt",
            notes_path=temp_output_dir / "notes.txt"
        )
        
        # Read generated HTML
        html_content = (temp_output_dir / "index.html").read_text()
        
        # Verify CSS is included
        assert "<style>" in html_content
        assert "font-family:" in html_content
        assert "max-width:" in html_content
        assert "border-radius:" in html_content
        
        # Verify responsive design
        assert "viewport" in html_content
        assert "width=device-width" in html_content