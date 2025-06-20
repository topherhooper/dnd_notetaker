import logging
import os
import shutil
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dnd_notetaker.utils import (
    save_text_output,
    setup_logging,
)


class TestSetupLogging:
    def test_setup_logging_returns_logger(self):
        logger = setup_logging("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_setup_logging_configures_level(self):
        logger = setup_logging("test_debug")
        assert logger.level == logging.DEBUG or logger.level == logging.NOTSET

    def test_setup_logging_has_handlers(self):
        logger = setup_logging("test_handlers")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)


class TestSaveTextOutput:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_text_output_creates_file(self):
        content = "Test content"
        prefix = "test"

        filepath = save_text_output(content, prefix, self.temp_dir)

        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            assert f.read() == content

    def test_save_text_output_creates_directory_if_not_exists(self):
        content = "Test content"
        prefix = "test"
        new_dir = os.path.join(self.temp_dir, "new_subdirectory")

        filepath = save_text_output(content, prefix, new_dir)

        assert os.path.exists(new_dir)
        assert os.path.exists(filepath)

    def test_save_text_output_filename_format(self):
        content = "Test content"
        prefix = "my_prefix"

        with patch("dnd_notetaker.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            filepath = save_text_output(content, prefix, self.temp_dir)

        filename = os.path.basename(filepath)
        assert filename == "my_prefix_20240101_120000.txt"

    def test_save_text_output_returns_correct_path(self):
        content = "Test content"
        prefix = "test"

        filepath = save_text_output(content, prefix, self.temp_dir)

        assert filepath.startswith(self.temp_dir)
        assert filepath.endswith(".txt")
        assert prefix in filepath

    def test_save_text_output_handles_unicode(self):
        content = "Test with unicode: 🎲 D&D 🐉"
        prefix = "unicode_test"

        filepath = save_text_output(content, prefix, self.temp_dir)

        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_text_output_handles_empty_content(self):
        content = ""
        prefix = "empty"

        filepath = save_text_output(content, prefix, self.temp_dir)

        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            assert f.read() == ""

    def test_save_text_output_handles_multiline_content(self):
        content = """Line 1
Line 2
Line 3"""
        prefix = "multiline"

        filepath = save_text_output(content, prefix, self.temp_dir)

        with open(filepath, "r") as f:
            assert f.read() == content


