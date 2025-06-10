import os
import shutil
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from dnd_notetaker.transcriber import Transcriber


class TestTranscriber:
    def setup_method(self):
        self.api_key = "test_api_key"
        self.temp_dir = tempfile.mkdtemp()

        # Mock the OpenAI client
        with patch("dnd_notetaker.transcriber.openai.OpenAI") as mock_openai_class:
            self.mock_client = MagicMock()
            mock_openai_class.return_value = self.mock_client
            self.transcriber = Transcriber(self.api_key)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        assert self.transcriber.model == "gpt-4o"
        assert hasattr(self.transcriber, "logger")
        assert hasattr(self.transcriber, "client")
        assert self.transcriber.client == self.mock_client

    @patch("dnd_notetaker.transcriber.openai.OpenAI")
    def test_init_creates_openai_client(self, mock_openai):
        transcriber = Transcriber("test_key")
        mock_openai.assert_called_once_with(api_key="test_key")

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    def test_get_transcript_success(
        self, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock the OpenAI response
        mock_transcript = "This is a test transcript."
        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        # Call get_transcript
        audio_path = "test_audio.mp3"
        transcript, filepath = self.transcriber.get_transcript(audio_path)

        # Verify
        assert transcript == mock_transcript
        assert filepath is None  # No output_dir provided

        # Verify API call
        self.mock_client.audio.transcriptions.create.assert_called_once_with(
            model="whisper-1", file=mock_file(), response_format="text"
        )

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    @patch("dnd_notetaker.transcriber.save_text_output")
    def test_get_transcript_with_output_dir(
        self, mock_save, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock the OpenAI response
        mock_transcript = "This is a test transcript."
        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        # Mock save_text_output
        expected_path = os.path.join(
            self.temp_dir, "raw_transcript_20240101_120000.txt"
        )
        mock_save.return_value = expected_path

        # Call get_transcript with output directory
        audio_path = "test_audio.mp3"
        transcript, filepath = self.transcriber.get_transcript(
            audio_path, self.temp_dir
        )

        # Verify
        assert transcript == mock_transcript
        assert filepath == expected_path

        # Verify save was called
        mock_save.assert_called_once_with(
            mock_transcript, "full_transcript", self.temp_dir
        )

    def test_get_transcript_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            self.transcriber.get_transcript("/non/existent/audio.mp3")

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    def test_get_transcript_api_error(
        self, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock API error
        self.mock_client.audio.transcriptions.create.side_effect = Exception(
            "API Error"
        )

        with pytest.raises(Exception, match="API Error"):
            self.transcriber.get_transcript("test_audio.mp3")

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    def test_get_transcript_empty_response(
        self, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock empty transcript
        self.mock_client.audio.transcriptions.create.return_value = ""

        transcript, filepath = self.transcriber.get_transcript("test_audio.mp3")

        assert transcript == ""
        assert filepath is None

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    def test_get_transcript_large_response(
        self, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock large transcript
        large_transcript = "This is a very long transcript. " * 1000
        self.mock_client.audio.transcriptions.create.return_value = large_transcript

        transcript, filepath = self.transcriber.get_transcript("test_audio.mp3")

        assert transcript == large_transcript
        assert len(transcript) > 30000  # Verify it's actually large

    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    @patch("os.path.getsize", return_value=1024)  # 1KB file
    @patch("dnd_notetaker.transcriber.save_text_output")
    def test_get_transcript_save_error(
        self, mock_save, mock_getsize, mock_access, mock_isfile, mock_exists, mock_file
    ):
        # Mock successful transcription but save fails
        mock_transcript = "This is a test transcript."
        self.mock_client.audio.transcriptions.create.return_value = mock_transcript
        mock_save.side_effect = Exception("Save error")

        with pytest.raises(Exception, match="Save error"):
            self.transcriber.get_transcript("test_audio.mp3", self.temp_dir)
