import os
import logging
import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from utils import setup_logging

class DocsUploader:
    def __init__(self):
        self.logger = setup_logging('DocsUploader')
        self.docs_service = None
        self.drive_service = None
        
        # If modifying these scopes, delete the token.json file.
        self.SCOPES = [
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]

    def setup_services(self):
        """Set up Google Docs and Drive services"""
        creds = None
        token_path = '.credentials/token.json'
        credentials_path = '.credentials/credentials.json'
        
        try:
            # Ensure .credentials directory exists
            os.makedirs(".credentials", exist_ok=True)
            
            # Check for credentials.json
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Google credentials not found at: {credentials_path}")
            
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists(token_path):
                self.logger.debug("Found existing token.json")
                try:
                    creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                except Exception as e:
                    self.logger.warning(f"Error loading existing token: {str(e)}")
                    # If token is invalid, remove it
                    os.remove(token_path)
                    creds = None
            
            # If no valid credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.debug("Refreshing expired credentials")
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        self.logger.warning(f"Error refreshing token: {str(e)}")
                        # If refresh fails, force new authentication
                        creds = None
                
                if not creds:
                    self.logger.info("Initiating new authentication flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                # Save the credentials for the next run
                try:
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    self.logger.debug("Saved new token.json")
                except Exception as e:
                    self.logger.warning(f"Error saving token: {str(e)}")

            # Create services
            self.docs_service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            
            self.logger.debug("Google services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up Google services: {str(e)}")
            raise

    def create_document(self, title):
        """Create a new Google Doc with the given title"""
        try:
            self.logger.info(f"Creating new document: {title}")
            document = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            self.logger.info(f"Created document with ID: {document.get('documentId')}")
            return document
            
        except Exception as e:
            if hasattr(e, 'reason') and 'SERVICE_DISABLED' in str(e):
                self.logger.error("Google Docs API is not enabled. Please enable it in the Google Cloud Console:")
                self.logger.error("1. Visit: https://console.cloud.google.com/apis/library/docs.googleapis.com")
                self.logger.error("2. Click 'Enable'")
                self.logger.error("3. Also enable the Drive API at: https://console.cloud.google.com/apis/library/drive.googleapis.com")
                self.logger.error("4. Wait a few minutes for the changes to propagate")
                raise RuntimeError("Google Docs API is not enabled") from e
            else:
                self.logger.error(f"Error creating document: {str(e)}")
                raise

    def update_document_content(self, doc_id, content):
        """Update the content of an existing Google Doc"""
        try:
            self.logger.info(f"Updating document: {doc_id}")
            
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1
                        },
                        'text': content
                    }
                }
            ]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            self.logger.info("Document content updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating document: {str(e)}")
            raise

    def share_document(self, doc_id, email=None, role='reader'):
        """Share the document with specific email or make it viewable with link"""
        try:
            if email:
                self.logger.info(f"Sharing document with {email}")
                permission = {
                    'type': 'user',
                    'role': role,
                    'emailAddress': email
                }
            else:
                self.logger.info("Making document accessible via link")
                permission = {
                    'type': 'anyone',
                    'role': role
                }
                
            self.drive_service.permissions().create(
                fileId=doc_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            
            self.logger.info("Sharing permissions updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error sharing document: {str(e)}")
            raise

    def upload_notes(self, notes_path, title=None, share_email=None):
        """Upload notes to Google Docs and optionally share"""
        try:
            if not os.path.exists(notes_path):
                raise FileNotFoundError(f"Notes file not found: {notes_path}")
            
            # Set up services if not already done
            if not self.docs_service:
                self.setup_services()
            
            # Read notes content
            with open(notes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use filename as title if not provided
            if not title:
                title = os.path.splitext(os.path.basename(notes_path))[0]
            
            # Create new document
            doc = self.create_document(title)
            doc_id = doc.get('documentId')
            
            # Update content
            self.update_document_content(doc_id, content)
            
            # Share if email provided
            if share_email:
                self.share_document(doc_id, share_email)
            
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            self.logger.info(f"Notes uploaded successfully: {doc_url}")
            
            return doc_url
            
        except Exception as e:
            self.logger.error(f"Error uploading notes: {str(e)}")
            raise

def main():
    """Main function for testing docs uploader independently"""
    logger = setup_logging('DocsUploaderMain')
    
    parser = argparse.ArgumentParser(description='Upload notes to Google Docs')
    parser.add_argument('--input', '-i', required=True, help='Path to the input notes file')
    parser.add_argument('--title', '-t', help='Title for the Google Doc')
    parser.add_argument('--share', '-s', help='Email address to share the document with')
    
    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")
    
    try:
        uploader = DocsUploader()
        doc_url = uploader.upload_notes(
            args.input,
            title=args.title,
            share_email=args.share
        )
        
        print(f"\nDocument uploaded successfully!")
        print(f"URL: {doc_url}")
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()