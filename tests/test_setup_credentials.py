import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

# Import from scripts directory
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)
from setup_credentials import CredentialSetup


class TestCredentialSetup:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.setup = CredentialSetup()

    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        assert self.setup.credentials_dir == Path(".credentials")
        assert self.setup.config_path == Path(".credentials/config.json")
        assert self.setup.config == {}

    def test_ensure_credentials_dir_creates_directory(self):
        assert not self.setup.credentials_dir.exists()

        with patch("builtins.print") as mock_print:
            self.setup.ensure_credentials_dir()

        assert self.setup.credentials_dir.exists()
        assert oct(self.setup.credentials_dir.stat().st_mode)[-3:] == "700"
        mock_print.assert_called_with("✓ Created .credentials directory")

    def test_ensure_credentials_dir_already_exists(self):
        self.setup.credentials_dir.mkdir()

        with patch("builtins.print") as mock_print:
            self.setup.ensure_credentials_dir()

        mock_print.assert_called_with("✓ .credentials directory already exists")

    @patch("builtins.input", side_effect=["n", "n"])
    def test_check_existing_config_no_overwrite(self, mock_input):
        # Create existing config
        self.setup.credentials_dir.mkdir()
        existing_config = {"openai_api_key": "test_key"}
        with open(self.setup.config_path, "w") as f:
            json.dump(existing_config, f)

        with patch("sys.exit") as mock_exit:
            self.setup.check_existing_config()
            mock_exit.assert_called_once_with(0)

    @patch("builtins.input", side_effect=["y"])
    def test_check_existing_config_overwrite(self, mock_input):
        # Create existing config
        self.setup.credentials_dir.mkdir()
        existing_config = {"openai_api_key": "test_key"}
        with open(self.setup.config_path, "w") as f:
            json.dump(existing_config, f)

        result = self.setup.check_existing_config()
        assert result is False

    @patch("builtins.input", side_effect=["n", "y"])
    def test_check_existing_config_update_mode(self, mock_input):
        # Create existing config
        self.setup.credentials_dir.mkdir()
        existing_config = {"openai_api_key": "test_key"}
        with open(self.setup.config_path, "w") as f:
            json.dump(existing_config, f)

        result = self.setup.check_existing_config()
        assert result is True
        assert self.setup.config == existing_config

    @patch("builtins.input", side_effect=["folder123"])
    def test_setup_drive_folder(self, mock_input):
        self.setup.setup_drive_folder()

        assert self.setup.config["drive_folder_id"] == "folder123"

    @patch("builtins.input", side_effect=[""])
    def test_setup_drive_folder_defaults(self, mock_input):
        # Set existing config
        self.setup.config = {
            "drive_folder_id": "existing_folder_id"
        }

        self.setup.setup_drive_folder(update_mode=True)

        # Should keep existing value
        assert self.setup.config["drive_folder_id"] == "existing_folder_id"

    @patch("getpass.getpass", return_value="test_api_key")
    def test_setup_openai_credentials(self, mock_getpass):
        self.setup.setup_openai_credentials()

        assert self.setup.config["openai_api_key"] == "test_api_key"

    def test_display_config_hides_passwords(self):
        config = {
            "openai_api_key": "sk-1234567890abcdefghijklmnop",
        }

        with patch("builtins.print") as mock_print:
            self.setup.display_config(config, hide_passwords=True)

        # Get the printed JSON
        printed_json = mock_print.call_args[0][0]
        printed_config = json.loads(printed_json)

        assert printed_config["openai_api_key"] == "sk-123...mnop"

    def test_save_config(self):
        self.setup.credentials_dir.mkdir()
        self.setup.config = {
            "openai_api_key": "test_key",
        }

        with patch("builtins.print"):
            self.setup.save_config()

        assert self.setup.config_path.exists()

        # Check file permissions (owner read/write only)
        assert oct(self.setup.config_path.stat().st_mode)[-3:] == "600"

        # Check content
        with open(self.setup.config_path, "r") as f:
            saved_config = json.load(f)
        assert saved_config == self.setup.config

    def test_verify_setup_all_good(self):
        # Create all required files
        self.setup.credentials_dir.mkdir()

        config = {
            "openai_api_key": "test_key",
        }

        with open(self.setup.config_path, "w") as f:
            json.dump(config, f)

        # Create service account credentials
        sa_path = self.setup.credentials_dir / "service_account.json"
        with open(sa_path, "w") as f:
            json.dump(
                {
                    "type": "service_account",
                    "client_email": "test@example.iam.gserviceaccount.com",
                },
                f,
            )

        with patch("builtins.print"):
            result = self.setup.verify_setup()

        assert result is True

    def test_verify_setup_missing_config(self):
        with patch("builtins.print"):
            result = self.setup.verify_setup()

        assert result is False

    def test_verify_setup_incomplete_config(self):
        self.setup.credentials_dir.mkdir()

        # Config missing required fields
        config = {
            # Missing openai_api_key
        }

        with open(self.setup.config_path, "w") as f:
            json.dump(config, f)

        with patch("builtins.print"):
            result = self.setup.verify_setup()

        assert result is False

    @patch("setup_credentials.CredentialSetup.verify_setup", return_value=True)
    @patch("setup_credentials.CredentialSetup.setup_google_auth")
    @patch("setup_credentials.CredentialSetup.save_config")
    @patch("setup_credentials.CredentialSetup.setup_openai_credentials")
    @patch("setup_credentials.CredentialSetup.setup_drive_folder")
    @patch(
        "setup_credentials.CredentialSetup.check_existing_config", return_value=False
    )
    @patch("setup_credentials.CredentialSetup.ensure_credentials_dir")
    @patch("setup_credentials.CredentialSetup.print_header")
    def test_run_complete_flow(
        self,
        mock_header,
        mock_ensure_dir,
        mock_check,
        mock_drive,
        mock_openai,
        mock_save,
        mock_google_auth,
        mock_verify,
    ):
        with patch("builtins.print"):
            self.setup.run()

        # Verify all steps were called
        mock_header.assert_called_once()
        mock_ensure_dir.assert_called_once()
        mock_check.assert_called_once()
        mock_drive.assert_called_once_with(False)
        mock_openai.assert_called_once_with(False)
        mock_save.assert_called_once()
        mock_google_auth.assert_called_once()
        mock_verify.assert_called_once()
