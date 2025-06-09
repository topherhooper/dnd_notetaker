import argparse
import logging
import os

from .auth_service_account import GoogleAuthenticator
from .utils import setup_logging


class DocsUploader:
    def __init__(self):
        self.logger = setup_logging("DocsUploader")
        self.docs_service = None
        self.drive_service = None

    def setup_services(self):
        """Set up Google Docs and Drive services using new authentication"""
        try:
            # Ensure .credentials directory exists
            os.makedirs(".credentials", exist_ok=True)

            auth = GoogleAuthenticator()
            self.drive_service, self.docs_service = auth.get_services()
            self.logger.debug("Google services initialized successfully")

        except Exception as e:
            self.logger.error(f"Error setting up Google services: {str(e)}")
            raise

    def create_document(self, title):
        """Create a new Google Doc with the given title"""
        try:
            self.logger.info(f"Creating new document: {title}")
            document = (
                self.docs_service.documents().create(body={"title": title}).execute()
            )

            self.logger.info(f"Created document with ID: {document.get('documentId')}")
            return document

        except Exception as e:
            if hasattr(e, "reason") and "SERVICE_DISABLED" in str(e):
                self.logger.error(
                    "Google Docs API is not enabled. Please enable it in the Google Cloud Console:"
                )
                self.logger.error(
                    "1. Visit: https://console.cloud.google.com/apis/library/docs.googleapis.com"
                )
                self.logger.error("2. Click 'Enable'")
                self.logger.error(
                    "3. Also enable the Drive API at: https://console.cloud.google.com/apis/library/drive.googleapis.com"
                )
                self.logger.error("4. Wait a few minutes for the changes to propagate")
                raise RuntimeError("Google Docs API is not enabled") from e
            else:
                self.logger.error(f"Error creating document: {str(e)}")
                raise

    def update_document_content(self, doc_id, content):
        """Update the content of an existing Google Doc"""
        try:
            self.logger.info(f"Updating document: {doc_id}")

            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()

            self.logger.info("Document content updated successfully")

        except Exception as e:
            self.logger.error(f"Error updating document: {str(e)}")
            raise

    def share_document(self, doc_id, email=None, role="reader"):
        """Share the document with specific email or make it viewable with link"""
        try:
            if email:
                self.logger.info(f"Sharing document with {email}")
                permission = {"type": "user", "role": role, "emailAddress": email}
            else:
                self.logger.info("Making document accessible via link")
                permission = {"type": "anyone", "role": role}

            self.drive_service.permissions().create(
                fileId=doc_id, body=permission, sendNotificationEmail=False
            ).execute()

            self.logger.info("Sharing permissions updated successfully")

        except Exception as e:
            self.logger.error(f"Error sharing document: {str(e)}")
            raise

    def upload_notes(
        self, notes_path, title=None, share_email=None, share_publicly=True
    ):
        """Upload notes to Google Docs and optionally share"""
        try:
            if not os.path.exists(notes_path):
                raise FileNotFoundError(f"Notes file not found: {notes_path}")

            # Set up services if not already done
            if not self.docs_service:
                self.setup_services()

            # Read notes content
            with open(notes_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Use filename as title if not provided
            if not title:
                title = os.path.splitext(os.path.basename(notes_path))[0]

            # Create new document
            doc = self.create_document(title)
            doc_id = doc.get("documentId")

            # Update content
            self.update_document_content(doc_id, content)

            # Share with specific email if provided
            if share_email:
                self.share_document(doc_id, share_email)

            # Make document publicly accessible with link by default
            if share_publicly:
                self.share_document(doc_id)  # No email means anyone with link
                self.logger.info("Document is now accessible to anyone with the link")

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            self.logger.info(f"Notes uploaded successfully: {doc_url}")

            return doc_url

        except Exception as e:
            self.logger.error(f"Error uploading notes: {str(e)}")
            raise


def main():
    """Main function for testing docs uploader independently"""
    logger = setup_logging("DocsUploaderMain")

    parser = argparse.ArgumentParser(description="Upload notes to Google Docs")
    parser.add_argument(
        "--input", "-i", required=True, help="Path to the input notes file"
    )
    parser.add_argument("--title", "-t", help="Title for the Google Doc")
    parser.add_argument(
        "--share", "-s", help="Email address to share the document with"
    )
    parser.add_argument(
        "--no-public-share",
        action="store_true",
        help="Do not make document publicly accessible with link",
    )

    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")

    try:
        uploader = DocsUploader()
        doc_url = uploader.upload_notes(
            args.input,
            title=args.title,
            share_email=args.share,
            share_publicly=not args.no_public_share,
        )

        print(f"\nDocument uploaded successfully!")
        print(f"URL: {doc_url}")
        if not args.no_public_share:
            print("Document is accessible to anyone with the link")

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
