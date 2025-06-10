import argparse
import email
import imaplib
import io
import json
import logging
import os
import re

from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

from .auth_service_account import GoogleAuthenticator


def setup_logging(name):
    """Configure logging with timestamps and appropriate formatting"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(name)


class EmailHandler:
    def __init__(self, credentials):
        self.logger = setup_logging("EmailHandler")
        self.credentials = credentials
        self.drive_service = None

        # Patterns for Google Drive links
        self.drive_patterns = [
            r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
            r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]

        # Initialize Drive service at startup
        self.setup_drive_service()

        self.logger.debug("EmailHandler initialized with Drive service")

    def setup_drive_service(self):
        """Set up Google Drive API service using new authentication"""
        auth = GoogleAuthenticator()
        self.drive_service, _ = auth.get_services()

    def sanitize_filename(self, filename):
        """Sanitize filename to be safe for all operating systems"""
        # Replace slashes with dashes
        filename = filename.replace("/", "-").replace("\\", "-")
        # Replace colons with dashes
        filename = filename.replace(":", "-")
        # Replace any other potentially problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "-")
        return filename

    def connect(self):
        """Establish IMAP connection"""
        self.logger.debug(
            f"Connecting to IMAP server: {self.credentials['imap_server']}"
        )
        self.mail = imaplib.IMAP4_SSL(self.credentials["imap_server"])
        self.mail.login(self.credentials["email"], self.credentials["password"])
        self.mail.select("INBOX")
        self.logger.debug("Successfully connected to email server")

    def process_email_content(self, email_message):
        """Process email content to find Drive links"""
        found_files = []

        try:
            if not self.drive_service:
                self.logger.info("Drive service not initialized, setting up now...")
                self.setup_drive_service()

            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        content = part.get_payload(decode=True).decode()
                    except Exception as e:
                        self.logger.error(f"Error decoding email content: {str(e)}")
                        continue

                    self.logger.debug(f"Checking content type: {content_type}")

                    # Extract and log all links for debugging
                    if "drive.google.com" in content:
                        self.logger.debug("Found Google Drive links in content")

                    # Extract all drive IDs from content
                    file_ids = []
                    for pattern in self.drive_patterns:
                        self.logger.debug(f"Trying pattern: {pattern}")
                        matches = re.finditer(pattern, content)
                        current_ids = [match.group(1) for match in matches]
                        if current_ids:
                            self.logger.debug(
                                f"Found IDs with pattern {pattern}: {current_ids}"
                            )
                        file_ids.extend(current_ids)

                    if not file_ids:
                        self.logger.debug("No Drive IDs found in this part")
                        continue

                    self.logger.info(f"Found {len(file_ids)} potential Drive files")

                    for file_id in file_ids:
                        try:
                            # Get file metadata
                            self.logger.debug(f"Checking file ID: {file_id}")
                            file_metadata = (
                                self.drive_service.files().get(fileId=file_id).execute()
                            )
                            mime_type = file_metadata.get("mimeType", "")

                            self.logger.info(
                                f"Found Drive file: {file_metadata['name']}"
                            )
                            self.logger.info(f"MIME type: {mime_type}")

                            # Look for video files
                            if "video" in mime_type:
                                self.logger.info("Found video file!")
                                return file_id
                            else:
                                self.logger.info(
                                    "Not a video file, continuing search..."
                                )

                        except Exception as e:
                            self.logger.error(
                                f"Error checking file {file_id}: {str(e)}",
                                exc_info=True,
                            )
                            continue

            return None

        except Exception as e:
            self.logger.error(
                f"Error in process_email_content: {str(e)}", exc_info=True
            )
            raise

    def download_from_drive(self, file_id, download_dir):
        """Download file from Google Drive"""
        if not self.drive_service:
            self.setup_drive_service()

        try:
            # Get file metadata with additional fields
            file_metadata = (
                self.drive_service.files()
                .get(fileId=file_id, fields="name,size,mimeType")
                .execute()
            )
            original_name = file_metadata["name"]
            mime_type = file_metadata.get("mimeType", "")
            file_size = int(file_metadata.get("size", 0))

            # Add extension if missing based on MIME type
            if not os.path.splitext(original_name)[1] and mime_type:
                mime_extensions = {
                    "video/mp4": ".mp4",
                    "video/webm": ".webm",
                    "video/quicktime": ".mov",
                    "video/x-msvideo": ".avi",
                    "video/x-matroska": ".mkv",
                }
                ext = mime_extensions.get(mime_type, "")
                if ext:
                    original_name += ext

            safe_filename = self.sanitize_filename(original_name)

            self.logger.info(f"Found Drive file: {original_name}")
            self.logger.info(f"MIME type: {mime_type}")
            self.logger.info(f"File size: {file_size / (1024*1024):.2f} MB")

            # Check if file already exists
            filepath = os.path.join(download_dir, safe_filename)
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if existing_size == file_size:
                    self.logger.info("=" * 60)
                    self.logger.info("SKIPPING DOWNLOAD - File already exists")
                    self.logger.info(f"File: {filepath}")
                    self.logger.info(f"Size: {file_size / (1024*1024):.2f} MB")
                    self.logger.info("=" * 60)
                    return filepath
                else:
                    self.logger.warning(f"File exists but size differs.")
                    self.logger.warning(
                        f"Expected: {file_size} bytes, Found: {existing_size} bytes"
                    )
                    self.logger.info("Redownloading...")
            else:
                self.logger.info("File doesn't exist. Starting download...")

            # Ensure directory exists
            os.makedirs(download_dir, exist_ok=True)

            # Download file directly to disk
            request = self.drive_service.files().get_media(fileId=file_id)

            # Open file for writing
            with open(filepath, "wb") as f:
                downloader = MediaIoBaseDownload(
                    f, request, chunksize=50 * 1024 * 1024
                )  # 50MB chunks
                done = False

                with tqdm(total=100, desc=f"Downloading {safe_filename}") as pbar:
                    last_progress = 0
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            pbar.update(progress - last_progress)
                            last_progress = progress

            self.logger.info(f"Download complete: {filepath}")

            # Log successful download
            final_size = os.path.getsize(filepath)
            self.logger.info("=" * 60)
            self.logger.info("DOWNLOAD COMPLETED SUCCESSFULLY")
            self.logger.info(f"File: {filepath}")
            self.logger.info(f"Size: {final_size / (1024*1024):.2f} MB")
            self.logger.info("=" * 60)

            return filepath

        except Exception as e:
            self.logger.error(f"Error downloading from Drive: {str(e)}")
            raise

    def download_recording(self, email_id, download_dir):
        """Process email and download recording from Drive"""
        try:
            _, msg_data = self.mail.fetch(email_id, "(RFC822)")
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            self.logger.info(f"Processing email: {email_message['subject']}")

            # Look for Drive link in email content
            file_id = self.process_email_content(email_message)
            if file_id:
                return self.download_from_drive(file_id, download_dir)

            return None

        except Exception as e:
            self.logger.error(f"Error processing email: {str(e)}")
            raise

    def check_existing_downloads(self, subject_filter, download_dir):
        """Check if we already have a downloaded file matching the subject"""
        if not os.path.exists(download_dir):
            return None

        # Look for video files that might be meeting recordings
        video_extensions = [".mp4", ".webm", ".mov", ".avi", ".mkv"]

        for filename in os.listdir(download_dir):
            # Check if it's a video file
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                # Check if filename contains relevant keywords
                if any(
                    keyword in filename
                    for keyword in ["DnD", "D&D", "Recording", subject_filter]
                ):
                    filepath = os.path.join(download_dir, filename)
                    file_size = os.path.getsize(filepath)
                    self.logger.info(
                        f"Found existing file: {filename} ({file_size / (1024*1024):.2f} MB)"
                    )
                    return filepath
        return None

    def download_meet_recording(self, subject_filter, download_dir):
        """Main method to find and download meeting recording"""
        try:
            # First check if we already have the file
            existing_file = self.check_existing_downloads(subject_filter, download_dir)
            if existing_file:
                self.logger.info("=" * 60)
                self.logger.info("USING EXISTING DOWNLOAD")
                self.logger.info(f"File: {existing_file}")
                self.logger.info("Skipping email search and download")
                self.logger.info("=" * 60)
                return existing_file

            # If not found, proceed with email search
            self.connect()

            # Search for relevant emails
            _, messages = self.mail.search(None, f'SUBJECT "{subject_filter}"')
            email_ids = messages[0].split() if messages[0] else []

            if not email_ids:
                raise Exception("No matching emails found")

            # Process each email in reverse order (newest first)
            for email_id in reversed(email_ids):
                filepath = self.download_recording(email_id, download_dir)
                if filepath:
                    return filepath

            raise Exception("No recordings found in matching emails")

        except Exception as e:
            self.logger.error(f"Error in download_meet_recording: {str(e)}")
            raise
        finally:
            if hasattr(self, "mail"):
                self.mail.logout()


def main():
    """Main function for testing email handler independently"""
    logger = setup_logging("EmailHandlerMain")

    parser = argparse.ArgumentParser(
        description="Download meeting recordings from email"
    )
    parser.add_argument("--output", "-o", help="Output directory", default="output")
    parser.add_argument(
        "--config", help="Path to config file", default=".credentials/config.json"
    )
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    logger.debug(f"Ensuring output directory exists: {args.output}")

    # Load config
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
        logger.debug("Config loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load config file: {str(e)}")
        raise

    # Create handler
    handler = EmailHandler(config["email"])

    try:
        # Try to download a recording
        logger.info("Starting download process...")
        filepath = handler.download_meet_recording("Meeting records", args.output)
        logger.info(f"Successfully downloaded recording to: {filepath}")

    except Exception as e:
        logger.error(f"Download process failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
