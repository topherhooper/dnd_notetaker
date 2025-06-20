#!/usr/bin/env python3
"""
Google Service Account Authentication Helper
Uses service account for authentication (no interactive login required)
"""

import json
import os
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleAuthenticator:
    """Handles Google authentication using service account"""

    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
    ]

    def __init__(self, credentials_dir=".credentials"):
        self.creds_dir = Path(credentials_dir)
        self.service_account_path = self.creds_dir / "service_account.json"

    def authenticate(self):
        """
        Authenticate using service account
        """
        if not self.service_account_path.exists():
            print(
                f"❌ Error: Service account file not found at {self.service_account_path}"
            )
            print("\nPlease set up a service account:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a service account and download the JSON key")
            print("3. Save it as .credentials/service_account.json")
            sys.exit(1)

        print("Using service account authentication...")
        return self._authenticate_service_account()

    def _authenticate_service_account(self):
        """Authenticate using service account credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(self.service_account_path), scopes=self.SCOPES
            )
            print("✓ Service account authentication successful")
            return credentials
        except Exception as e:
            print(f"❌ Service account authentication failed: {e}")
            raise

    def get_services(self):
        """Get authenticated Google Drive and Docs services"""
        creds = self.authenticate()

        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)

        return drive_service, docs_service


def setup_service_account():
    """Interactive setup for service account credentials"""
    print("=== Service Account Setup ===")
    print()
    print("To use a service account:")
    print()
    print("1. Go to https://console.cloud.google.com/")
    print("2. Select your project")
    print("3. Go to 'IAM & Admin' > 'Service Accounts'")
    print("4. Click 'Create Service Account'")
    print("5. Give it a name (e.g., 'dnd-notetaker')")
    print("6. Grant roles:")
    print("   - 'Viewer' for Google Drive (to download recordings)")
    print("   - 'Google Docs Editor' (to create/edit documents)")
    print("7. Click 'Create Key' > JSON")
    print("8. Save the file as '.credentials/service_account.json'")
    print()
    print("For shared drives, you may also need to:")
    print("- Share the drive/folders with the service account email")
    print("- Or use domain-wide delegation if in a Google Workspace")
    print()
    input("Press Enter when you've saved the service account file...")

    service_path = Path(".credentials/service_account.json")
    if service_path.exists():
        print("✓ Found service_account.json")
        # Validate the file
        try:
            with open(service_path) as f:
                data = json.load(f)
                if "type" in data and data["type"] == "service_account":
                    print("✓ Valid service account file")
                    print(
                        f"✓ Service account email: {data.get('client_email', 'unknown')}"
                    )
                    return True
        except Exception as e:
            print(f"❌ Invalid service account file: {e}")
    else:
        print("❌ service_account.json not found")

    return False


