"""Tests for the prose-style note generator"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import openai

from dnd_notetaker.note_generator import NoteGenerator
from dnd_notetaker.config import Config


class TestNoteGenerator:
    """Test note generation functionality"""
    
    @pytest.fixture
    def generator(self):
        """Create note generator with mock client"""
        mock_config = Mock(spec=Config)
        mock_config.dry_run = False
        with patch('openai.OpenAI'):
            return NoteGenerator("test-api-key", mock_config)
    
    @pytest.fixture
    def mock_response(self):
        """Create mock OpenAI response"""
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Generated prose notes"
        return response
    
    def test_init(self):
        """Test note generator initialization"""
        mock_config = Mock(spec=Config)
        mock_config.dry_run = False
        with patch('openai.OpenAI') as mock_openai:
            generator = NoteGenerator("test-key", mock_config)
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_generate_single_chunk(self, generator, mock_response):
        """Test generating notes from a single chunk transcript"""
        # Setup mock
        generator.client.chat.completions.create.return_value = mock_response
        
        # Generate notes
        transcript = "This is a test transcript"
        result = generator.generate(transcript)
        
        # Verify
        assert result == "Generated prose notes"
        generator.client.chat.completions.create.assert_called_once()
        
        # Check API call parameters
        call_args = generator.client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == 'o4-mini'
        assert len(call_args.kwargs['messages']) == 2
        assert 'continuous prose' in call_args.kwargs['messages'][0]['content']
        assert transcript in call_args.kwargs['messages'][1]['content']
    
    def test_generate_multiple_chunks(self, generator):
        """Test generating notes from a long transcript with multiple chunks"""
        # Create a very long transcript
        long_transcript = "This is a very long transcript. " * 10000
        
        # Setup mock responses for chunks
        chunk_responses = []
        for i in range(3):
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message.content = f"Chunk {i} summary"
            chunk_responses.append(response)
        
        # Add final combination response
        final_response = Mock()
        final_response.choices = [Mock()]
        final_response.choices[0].message.content = "Combined final notes"
        
        # Calculate expected number of chunks
        expected_chunks = len(generator._split_transcript(long_transcript))
        all_responses = []
        for i in range(expected_chunks):
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message.content = f"Chunk {i} summary"
            all_responses.append(response)
        all_responses.append(final_response)  # Add combination response
        
        generator.client.chat.completions.create.side_effect = all_responses
        
        # Generate notes
        result = generator.generate(long_transcript)
        
        # Verify
        assert result == "Combined final notes"
        assert generator.client.chat.completions.create.call_count == expected_chunks + 1  # chunks + 1 combination
    
    def test_split_transcript(self, generator):
        """Test transcript splitting logic"""
        # Test short transcript (no split)
        short_transcript = "This is short."
        chunks = generator._split_transcript(short_transcript)
        assert len(chunks) == 1
        assert chunks[0] == short_transcript
        
        # Test long transcript (should split)
        long_transcript = "This is a sentence. " * 5000
        chunks = generator._split_transcript(long_transcript, max_tokens=1000)
        assert len(chunks) > 1
        
        # Verify chunks don't exceed max size
        max_chars = 1000 * 4  # 1 token ≈ 4 chars
        for chunk in chunks:
            assert len(chunk) <= max_chars * 1.2  # Allow some margin
    
    def test_generate_notes_error_handling(self, generator):
        """Test error handling in note generation"""
        # Setup mock to raise error
        generator.client.chat.completions.create.side_effect = Exception("API Error")
        
        # Generate notes and expect error
        with pytest.raises(Exception, match="API Error"):
            generator.generate("Test transcript")
    
    def test_generate_chunk_summary(self, generator, mock_response):
        """Test generating summary for a single chunk"""
        # Setup mock
        generator.client.chat.completions.create.return_value = mock_response
        
        # Generate chunk summary
        result = generator._generate_chunk_summary("Chunk content", 2, 5)
        
        # Verify
        assert result == "Generated prose notes"
        
        # Check system prompt mentions chunk numbers
        call_args = generator.client.chat.completions.create.call_args
        system_prompt = call_args.kwargs['messages'][0]['content']
        assert "part 2 of 5" in system_prompt
    
    def test_combine_summaries(self, generator):
        """Test combining multiple summaries"""
        # Setup mock
        combined_response = Mock()
        combined_response.choices = [Mock()]
        combined_response.choices[0].message.content = "Combined narrative"
        generator.client.chat.completions.create.return_value = combined_response
        
        # Combine summaries
        summaries = ["Summary 1", "Summary 2", "Summary 3"]
        result = generator._combine_summaries(summaries)
        
        # Verify
        assert result == "Combined narrative"
        
        # Check all summaries were included
        call_args = generator.client.chat.completions.create.call_args
        user_content = call_args.kwargs['messages'][1]['content']
        for summary in summaries:
            assert summary in user_content
    
    def test_prose_style_requirements(self, generator, mock_response):
        """Test that prose style requirements are in prompts"""
        # Setup mock
        generator.client.chat.completions.create.return_value = mock_response
        
        # Generate notes
        generator.generate("Test transcript")
        
        # Check system prompt includes prose requirements
        call_args = generator.client.chat.completions.create.call_args
        system_prompt = call_args.kwargs['messages'][0]['content']
        
        assert "NO bullet points" in system_prompt
        assert "continuous prose" in system_prompt
        assert "natural narrative" in system_prompt
        assert "chronological flow" in system_prompt