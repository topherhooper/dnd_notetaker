from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dnd_notetaker.docs_uploader import DocsUploader


class TestDocsUploader:
    @patch("dnd_notetaker.docs_uploader.GoogleAuthenticator")
    def test_upload_notes_with_public_sharing(self, mock_auth):
        """Test that documents are shared publicly by default"""
        # Setup mocks with proper chaining
        mock_drive_service = Mock()
        mock_docs_service = Mock()

        # Setup chain for documents().create()
        mock_create_chain = Mock()
        mock_create_chain.execute.return_value = {"documentId": "test-doc-id"}
        mock_docs_service.documents.return_value.create.return_value = mock_create_chain

        # Setup chain for documents().batchUpdate()
        mock_update_chain = Mock()
        mock_update_chain.execute.return_value = {}
        mock_docs_service.documents.return_value.batchUpdate.return_value = (
            mock_update_chain
        )

        # Setup chain for permissions().create()
        mock_perm_chain = Mock()
        mock_perm_chain.execute.return_value = {}
        mock_drive_service.permissions.return_value.create.return_value = (
            mock_perm_chain
        )

        mock_auth.return_value.get_services.return_value = (
            mock_drive_service,
            mock_docs_service,
        )

        # Create uploader and test
        uploader = DocsUploader()
        uploader.setup_services()

        # Create a temporary file for testing
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            test_file = f.name

        try:
            # Test upload with default public sharing
            doc_url = uploader.upload_notes(test_file, title="Test Doc")

            # Verify document was created
            mock_docs_service.documents.return_value.create.assert_called_once_with(
                body={"title": "Test Doc"}
            )

            # Verify document was updated with content
            mock_docs_service.documents.return_value.batchUpdate.assert_called_once()

            # Verify public sharing was applied
            mock_drive_service.permissions.return_value.create.assert_called_once()
            perm_call = mock_drive_service.permissions.return_value.create.call_args
            assert perm_call[1]["body"]["type"] == "anyone"
            assert perm_call[1]["body"]["role"] == "reader"
            assert perm_call[1]["fileId"] == "test-doc-id"

            # Verify the returned URL
            assert doc_url == "https://docs.google.com/document/d/test-doc-id/edit"

        finally:
            import os

            os.unlink(test_file)

    @patch("dnd_notetaker.docs_uploader.GoogleAuthenticator")
    def test_upload_notes_without_public_sharing(self, mock_auth):
        """Test that public sharing can be disabled"""
        # Setup mocks with proper chaining
        mock_drive_service = Mock()
        mock_docs_service = Mock()

        # Setup chain for documents().create()
        mock_create_chain = Mock()
        mock_create_chain.execute.return_value = {"documentId": "test-doc-id"}
        mock_docs_service.documents.return_value.create.return_value = mock_create_chain

        # Setup chain for documents().batchUpdate()
        mock_update_chain = Mock()
        mock_update_chain.execute.return_value = {}
        mock_docs_service.documents.return_value.batchUpdate.return_value = (
            mock_update_chain
        )

        # Setup chain for permissions().create()
        mock_perm_chain = Mock()
        mock_perm_chain.execute.return_value = {}
        mock_drive_service.permissions.return_value.create.return_value = (
            mock_perm_chain
        )

        mock_auth.return_value.get_services.return_value = (
            mock_drive_service,
            mock_docs_service,
        )

        # Create uploader and test
        uploader = DocsUploader()
        uploader.setup_services()

        # Create a temporary file for testing
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            test_file = f.name

        try:
            # Test upload without public sharing
            doc_url = uploader.upload_notes(
                test_file, title="Test Doc", share_publicly=False
            )

            # Verify document was created and updated
            mock_docs_service.documents.return_value.create.assert_called_once_with(
                body={"title": "Test Doc"}
            )
            mock_docs_service.documents.return_value.batchUpdate.assert_called_once()

            # Verify NO sharing permissions were applied
            mock_drive_service.permissions.return_value.create.assert_not_called()

            # Verify the returned URL
            assert doc_url == "https://docs.google.com/document/d/test-doc-id/edit"

        finally:
            import os

            os.unlink(test_file)
