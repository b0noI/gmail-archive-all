# test_gmail_archiver.py

import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import os
import logging

# Import the script to be tested
import gmail_archiver

# Suppress logging output during tests for cleaner test results
# You can enable it for debugging by commenting out the next line
logging.disable(logging.CRITICAL)


class TestGmailArchiver(unittest.TestCase):

    def setUp(self):
        # Reset any potentially problematic global state if necessary,
        # e.g., if gmail_archiver.logger was configured in a way that affects tests.
        # For now, disabling logging globally in tests is simpler.
        pass

    @patch('gmail_archiver.os.path.exists')
    @patch('gmail_archiver.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_archiver.build')
    @patch('gmail_archiver.Credentials.from_authorized_user_file')
    def test_authenticate_gmail_token_valid(self, mock_from_user_file, mock_build, mock_flow, mock_exists):
        """Test authentication when token.json exists and is valid."""
        mock_exists.return_value = True  # token.json exists
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.refresh_token = True # Has a refresh token just in case, though not used here
        mock_from_user_file.return_value = mock_creds
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        service = gmail_archiver.authenticate_gmail()

        mock_from_user_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, gmail_archiver.SCOPES)
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        self.assertEqual(service, mock_service)
        mock_flow.assert_not_called() # Should not start new flow

    @patch('gmail_archiver.os.path.exists')
    @patch('gmail_archiver.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_archiver.build')
    @patch('gmail_archiver.Credentials.from_authorized_user_file')
    def test_authenticate_gmail_token_expired_refresh_success(self, mock_from_user_file, mock_build, mock_flow, mock_exists):
        """Test authentication when token.json exists, is expired, and refresh succeeds."""
        mock_exists.side_effect = lambda path: path == gmail_archiver.TOKEN_FILE # token.json exists
        
        mock_creds = MagicMock()
        mock_creds.valid = False # Initially invalid
        mock_creds.expired = True
        mock_creds.refresh_token = True
        
        # Make creds valid after refresh
        def refresh_creds_effect(request):
            mock_creds.valid = True 
            mock_creds.expired = False
        mock_creds.refresh.side_effect = refresh_creds_effect
        
        mock_from_user_file.return_value = mock_creds
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock open for saving the refreshed token
        with patch('builtins.open', mock_open()) as mock_file:
            service = gmail_archiver.authenticate_gmail()

        mock_from_user_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, gmail_archiver.SCOPES)
        mock_creds.refresh.assert_called_once()
        mock_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, 'w') # Token saved
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        self.assertEqual(service, mock_service)
        mock_flow.assert_not_called()

    @patch('gmail_archiver.os.path.exists')
    @patch('gmail_archiver.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_archiver.build')
    @patch('gmail_archiver.Credentials.from_authorized_user_file')
    def test_authenticate_gmail_token_expired_refresh_fail(self, mock_from_user_file, mock_build, mock_flow_constructor, mock_exists):
        """Test authentication when token.json exists, is expired, and refresh fails."""
        
        # token.json exists, credentials.json also exists for the fallback flow
        def os_path_exists_side_effect(path):
            if path == gmail_archiver.TOKEN_FILE:
                return True # token.json exists
            if path == 'credentials.json':
                return True # credentials.json exists for fallback
            return False
        mock_exists.side_effect = os_path_exists_side_effect

        mock_initial_creds = MagicMock()
        mock_initial_creds.valid = False      # Credentials are not valid
        mock_initial_creds.expired = True     # Should attempt refresh
        mock_initial_creds.refresh_token = "mock_refresh_token" # Should attempt refresh
        mock_initial_creds.refresh.side_effect = Exception("Refresh failed") # Refresh attempt fails
        mock_from_user_file.return_value = mock_initial_creds
        
        # Mock the flow that should run after refresh fails
        mock_flow_instance = MagicMock()
        mock_new_creds = MagicMock()
        mock_new_creds.valid = True # New creds from flow are valid
        mock_flow_instance.run_local_server.return_value = mock_new_creds
        mock_flow_constructor.return_value = mock_flow_instance
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        with patch('builtins.open', mock_open()) as mock_file:
            service = gmail_archiver.authenticate_gmail()

        mock_from_user_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, gmail_archiver.SCOPES)
        mock_initial_creds.refresh.assert_called_once()
        mock_flow_constructor.assert_called_once_with('credentials.json', gmail_archiver.SCOPES)
        mock_flow_instance.run_local_server.assert_called_once_with(port=0)
        mock_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, 'w') # New token saved
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_new_creds)
        self.assertEqual(service, mock_service)
        # mock_initial_creds.refresh.assert_called_once() # We are not testing this mock directly here,
                                                        # but rather the consequence of its failure.


    @patch('gmail_archiver.os.path.exists')
    @patch('gmail_archiver.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail_archiver.build')
    def test_authenticate_gmail_no_token_new_flow_success(self, mock_build, mock_flow_constructor, mock_exists):
        """Test authentication when no token.json, new OAuth flow runs."""
        # token.json does not exist, credentials.json does
        mock_exists.side_effect = lambda path: path == 'credentials.json'

        mock_flow_instance = MagicMock()
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_flow_constructor.return_value = mock_flow_instance
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        with patch('builtins.open', mock_open()) as mock_file:
            service = gmail_archiver.authenticate_gmail()

        mock_exists.assert_any_call(gmail_archiver.TOKEN_FILE) # Check for token.json
        mock_exists.assert_any_call('credentials.json')    # Check for credentials.json
        mock_flow_constructor.assert_called_once_with('credentials.json', gmail_archiver.SCOPES)
        mock_flow_instance.run_local_server.assert_called_once_with(port=0)
        mock_file.assert_called_once_with(gmail_archiver.TOKEN_FILE, 'w')
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        self.assertEqual(service, mock_service)

    @patch('gmail_archiver.os.path.exists')
    def test_authenticate_gmail_credentials_json_not_found(self, mock_exists):
        """Test authentication when credentials.json is not found."""
        # token.json does not exist, credentials.json also does not exist
        mock_exists.return_value = False 
        
        service = gmail_archiver.authenticate_gmail()
        self.assertIsNone(service)
        # Check that it logged an error (requires more complex logging capture or checking stderr)

    @patch('gmail_archiver.os.path.exists')
    @patch('gmail_archiver.InstalledAppFlow.from_client_secrets_file')
    def test_authenticate_gmail_flow_exception(self, mock_flow_constructor, mock_exists):
        """Test authentication when OAuth flow raises an exception."""
        mock_exists.side_effect = lambda path: path == 'credentials.json' # No token, creds.json exists
        mock_flow_constructor.side_effect = Exception("Flow error")

        service = gmail_archiver.authenticate_gmail()
        self.assertIsNone(service)

    @patch('gmail_archiver.build', side_effect=Exception("Build error"))
    @patch('gmail_archiver.Credentials.from_authorized_user_file')
    @patch('gmail_archiver.os.path.exists', return_value=True) # token.json exists
    def test_authenticate_gmail_build_service_fails(self, mock_exists, mock_from_user_file, mock_build):
        """Test authentication when building the Gmail service fails."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_user_file.return_value = mock_creds

        service = gmail_archiver.authenticate_gmail()
        self.assertIsNone(service)
        mock_build.assert_called_once()


    def test_fetch_inbox_emails_success_single_page(self):
        """Test fetching emails successfully with a single page of results."""
        mock_service = MagicMock()
        mock_messages_resource = mock_service.users().messages()
        
        # Simulate API response for list method
        mock_list_response = {
            'messages': [
                {'id': 'msg1', 'threadId': 'thread1'},
                {'id': 'msg2', 'threadId': 'thread2'}
            ]
            # No 'nextPageToken' means it's the only page
        }
        # list().execute() is the first call
        mock_list_initial_request = MagicMock()
        mock_list_initial_request.execute.return_value = mock_list_response
        mock_messages_resource.list.return_value = mock_list_initial_request
        
        # list_next() is called, and for a single page, it should return None
        mock_messages_resource.list_next.return_value = None 

        message_ids = gmail_archiver.fetch_inbox_emails(mock_service)

        mock_messages_resource.list.assert_called_once_with(userId='me', labelIds=['INBOX'])
        mock_list_initial_request.execute.assert_called_once() # Execute on the first request
        
        # list_next should be called once, after processing the first (and only) page
        mock_messages_resource.list_next.assert_called_once_with(
            previous_request=mock_list_initial_request, 
            previous_response=mock_list_response
        )
        self.assertEqual(message_ids, ['msg1', 'msg2'])

    def test_fetch_inbox_emails_success_multiple_pages(self):
        """Test fetching emails successfully with pagination."""
        mock_service = MagicMock()
        mock_messages_resource = mock_service.users().messages()

        # Simulate API responses for pagination
        mock_list_response_page1 = {
            'messages': [{'id': 'msg1'}],
            'nextPageToken': 'pageToken123'
        }
        mock_list_response_page2 = {
            'messages': [{'id': 'msg2'}]
            # No 'nextPageToken' means this is the last page
        }
        
        # list().execute() will be called first
        # list_next().execute() will be called for the second page
        # Need to make list() and list_next() distinct mocks if list_next is called on the original list() object
        
        mock_list_initial_request = MagicMock()
        mock_list_initial_request.execute.return_value = mock_list_response_page1
        mock_messages_resource.list.return_value = mock_list_initial_request

        mock_list_next_request = MagicMock()
        mock_list_next_request.execute.return_value = mock_list_response_page2
        # This setup assumes list_next is called with (previous_request, previous_response)
        mock_messages_resource.list_next.side_effect = [mock_list_next_request, None]


        message_ids = gmail_archiver.fetch_inbox_emails(mock_service)

        # Check calls
        mock_messages_resource.list.assert_called_once_with(userId='me', labelIds=['INBOX'])
        mock_list_initial_request.execute.assert_called_once()
        
        # Check that list_next was called correctly
        calls_to_list_next = mock_messages_resource.list_next.call_args_list
        self.assertEqual(len(calls_to_list_next), 2)
        self.assertEqual(calls_to_list_next[0][1]['previous_request'], mock_list_initial_request)
        self.assertEqual(calls_to_list_next[0][1]['previous_response'], mock_list_response_page1)
        
        # Check that the second request (from list_next) was executed
        mock_list_next_request.execute.assert_called_once()

        self.assertEqual(message_ids, ['msg1', 'msg2'])


    def test_fetch_inbox_emails_empty(self):
        """Test fetching emails when the inbox is empty."""
        mock_service = MagicMock()
        mock_messages_resource = mock_service.users().messages()
        mock_list_response = {'messages': []} # Empty messages list
        mock_messages_resource.list.return_value.execute.return_value = mock_list_response

        message_ids = gmail_archiver.fetch_inbox_emails(mock_service)

        mock_messages_resource.list.assert_called_once_with(userId='me', labelIds=['INBOX'])
        self.assertEqual(message_ids, [])

    def test_fetch_inbox_emails_no_messages_key(self):
        """Test fetching emails when the response has no 'messages' key."""
        mock_service = MagicMock()
        mock_messages_resource = mock_service.users().messages()
        mock_list_response = {} # No 'messages' key
        mock_messages_resource.list.return_value.execute.return_value = mock_list_response

        message_ids = gmail_archiver.fetch_inbox_emails(mock_service)

        mock_messages_resource.list.assert_called_once_with(userId='me', labelIds=['INBOX'])
        self.assertEqual(message_ids, [])

    def test_fetch_inbox_emails_api_error(self):
        """Test fetching emails when the API call raises an error."""
        mock_service = MagicMock()
        mock_messages_resource = mock_service.users().messages()
        mock_messages_resource.list.return_value.execute.side_effect = gmail_archiver.HttpError(
            MagicMock(status=500), b"API Error"
        )

        message_ids = gmail_archiver.fetch_inbox_emails(mock_service)
        self.assertEqual(message_ids, [])
        # Check logging for error (optional, requires log capture)

    def test_archive_emails_success(self):
        """Test archiving emails successfully."""
        mock_service = MagicMock()
        mock_users = mock_service.users.return_value
        mock_messages = mock_users.messages.return_value
        
        # When mock_messages.modify is called, it returns a new mock (mock_modify_request)
        # each time to simulate separate request objects.
        # We need to collect these to check their .execute() calls.
        execute_mocks = [MagicMock() for _ in range(3)]
        mock_modify_requests = [MagicMock(execute=exec_mock) for exec_mock in execute_mocks]
        
        # Set modify to return a different mock_modify_request on each call
        mock_messages.modify.side_effect = mock_modify_requests

        message_ids = ['msg1', 'msg2', 'msg3']
        archived_count = gmail_archiver.archive_emails(mock_service, message_ids)

        expected_body = {'removeLabelIds': ['INBOX']}
        calls_to_modify = [
            call(userId='me', id='msg1', body=expected_body),
            call(userId='me', id='msg2', body=expected_body),
            call(userId='me', id='msg3', body=expected_body)
        ]
        mock_messages.modify.assert_has_calls(calls_to_modify, any_order=False)
        
        for exec_mock in execute_mocks:
            exec_mock.assert_called_once() # Each execute mock should be called once
            
        self.assertEqual(archived_count, len(message_ids))

    def test_archive_emails_empty_list(self):
        """Test archiving with an empty list of message IDs."""
        mock_service = MagicMock()
        mock_users = mock_service.users.return_value
        mock_messages = mock_users.messages.return_value
        
        message_ids = []
        archived_count = gmail_archiver.archive_emails(mock_service, message_ids)

        mock_messages.modify.assert_not_called()
        self.assertEqual(archived_count, 0)

    def test_archive_emails_api_error_on_one_email(self):
        """Test archiving when an API error occurs for one email."""
        mock_service = MagicMock()
        mock_users = mock_service.users.return_value
        mock_messages = mock_users.messages.return_value

        # Setup three separate execute mocks for three calls to modify
        execute_mock_msg1 = MagicMock()
        execute_mock_msg2 = MagicMock()
        execute_mock_msg3 = MagicMock()

        # Define side effects for each execute call
        execute_mock_msg1.return_value = None # Success for msg1
        execute_mock_msg2.side_effect = gmail_archiver.HttpError(MagicMock(status=500), b"API Error on msg2") # Error for msg2
        execute_mock_msg3.return_value = None # Success for msg3
        
        # Each call to modify returns a mock that has one of these execute mocks
        mock_modify_request_msg1 = MagicMock(execute=execute_mock_msg1)
        mock_modify_request_msg2 = MagicMock(execute=execute_mock_msg2)
        mock_modify_request_msg3 = MagicMock(execute=execute_mock_msg3)

        mock_messages.modify.side_effect = [
            mock_modify_request_msg1,
            mock_modify_request_msg2,
            mock_modify_request_msg3
        ]
        
        message_ids = ['msg1', 'msg2', 'msg3']
        archived_count = gmail_archiver.archive_emails(mock_service, message_ids)

        expected_body = {'removeLabelIds': ['INBOX']}
        calls_to_modify = [
            call(userId='me', id='msg1', body=expected_body),
            call(userId='me', id='msg2', body=expected_body),
            call(userId='me', id='msg3', body=expected_body)
        ]
        mock_messages.modify.assert_has_calls(calls_to_modify, any_order=False)
        
        execute_mock_msg1.assert_called_once()
        execute_mock_msg2.assert_called_once()
        execute_mock_msg3.assert_called_once()
        
        self.assertEqual(archived_count, 2) # msg1 and msg3 should be archived

    @patch('gmail_archiver.authenticate_gmail')
    @patch('gmail_archiver.fetch_inbox_emails')
    @patch('gmail_archiver.archive_emails')
    def test_main_flow_successful_archival(self, mock_archive, mock_fetch, mock_auth):
        """Test the main function flow with successful authentication, fetch, and archive."""
        mock_service = MagicMock()
        mock_auth.return_value = mock_service
        
        mock_message_ids = ['id1', 'id2']
        mock_fetch.return_value = mock_message_ids
        
        mock_archive.return_value = len(mock_message_ids)

        gmail_archiver.main()

        mock_auth.assert_called_once()
        mock_fetch.assert_called_once_with(mock_service)
        mock_archive.assert_called_once_with(mock_service, mock_message_ids)

    @patch('gmail_archiver.authenticate_gmail', return_value=None)
    @patch('gmail_archiver.fetch_inbox_emails')
    @patch('gmail_archiver.archive_emails')
    def test_main_flow_auth_fails(self, mock_archive, mock_fetch, mock_auth):
        """Test the main function flow when authentication fails."""
        gmail_archiver.main()
        mock_auth.assert_called_once()
        mock_fetch.assert_not_called()
        mock_archive.assert_not_called()

    @patch('gmail_archiver.authenticate_gmail')
    @patch('gmail_archiver.fetch_inbox_emails', return_value=[]) # No emails fetched
    @patch('gmail_archiver.archive_emails')
    def test_main_flow_no_emails_to_archive(self, mock_archive, mock_fetch, mock_auth):
        """Test the main function flow when no emails are fetched."""
        mock_service = MagicMock()
        mock_auth.return_value = mock_service

        gmail_archiver.main()

        mock_auth.assert_called_once()
        mock_fetch.assert_called_once_with(mock_service)
        mock_archive.assert_not_called() # archive_emails should not be called if list is empty

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    # Re-enable logging if it was disabled for tests, if running interactively
    # logging.disable(logging.NOTSET)
