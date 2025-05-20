# gmail_archiver.py
#
# This script connects to a Gmail account using OAuth 2.0,
# fetches all emails from the INBOX, and archives them.
#
# PREREQUISITES:
# 1. Google Cloud Platform (GCP) Project:
#    - If you don't have one, create a project at https://console.cloud.google.com/.
# 2. Enable Gmail API:
#    - In your GCP project, navigate to "APIs & Services" > "Library".
#    - Search for "Gmail API" and enable it.
# 3. Configure OAuth Consent Screen:
#    - In "APIs & Services" > "OAuth consent screen".
#    - Choose "External" (or "Internal" if applicable).
#    - Fill in the required information (App name, User support email, Developer contact information).
#    - Add the scope: "../auth/gmail.modify"
# 4. Create OAuth 2.0 Credentials:
#    - In "APIs & Services" > "Credentials".
#    - Click "Create Credentials" > "OAuth client ID".
#    - Select "Desktop app" as the Application type.
#    - Name it (e.g., "Gmail Archiver Script").
#    - After creation, download the JSON file.
#    - **IMPORTANT**: Rename the downloaded JSON file to `credentials.json`
#      and place it in the same directory as this script.

import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Read/write access (needed to archive)
LOG_FILE = 'gmail_archiver.log'
TOKEN_FILE = 'token.json' # Stores user's access and refresh tokens

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

def authenticate_gmail():
    """Authenticates the user with Gmail API using OAuth 2.0.
    Manages token creation and refresh.
    Returns:
        googleapiclient.discovery.Resource: An authorized Gmail API service instance.
    """
    creds = None
    creds_were_modified_and_need_saving = False

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Loaded credentials from token.json")
        except Exception as e:
            logger.warning(f"Could not load token.json: {e}. Will attempt to re-authenticate.")
            creds = None

    if creds: # If token file loaded something
        if creds.valid:
            logger.info("Existing credentials are valid.")
        elif creds.expired and creds.refresh_token:
            logger.info("Existing credentials expired. Attempting to refresh token...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.")
                creds_were_modified_and_need_saving = True # Refreshed token needs saving
            except Exception as e:
                logger.error(f"Error refreshing token: {e}. Will attempt new OAuth flow.")
                creds = None # Nullify to trigger new flow logic below
        else: # Not valid, and not refreshable (e.g. revoked, malformed, no refresh_token)
            logger.info("Loaded credentials are not valid and cannot be refreshed. Attempting new OAuth flow.")
            creds = None # Nullify to trigger new flow logic below
    
    # If creds are None at this point (either never loaded, failed to load, failed to refresh, or invalid and not refreshable)
    # then we need to attempt a new OAuth flow.
    if not creds: 
        logger.info("Attempting new OAuth flow as existing credentials are not sufficient or available.")
        if not os.path.exists('credentials.json'):
            logger.error("OAuth credentials file 'credentials.json' not found.")
            logger.error("Please follow the PREREQUISITES section in the script's comments to set it up.")
            return None
        try:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds_new = flow.run_local_server(port=0) # Use a temporary variable
            if creds_new: # Check if new creds were actually obtained
                creds = creds_new # Assign to main creds variable
                logger.info("OAuth flow completed. Credentials obtained.")
                creds_were_modified_and_need_saving = True # New token needs saving
            else:
                logger.error("OAuth flow did not return credentials.")
                # creds remains None, will be caught by final check
        except FileNotFoundError: 
            logger.error("credentials.json not found during OAuth flow. Please ensure it's in the same directory.")
            return None
        except Exception as e:
            logger.error(f"Error during OAuth flow: {e}")
            return None

    # Save token if it was modified (refreshed or new) and creds are available
    if creds_were_modified_and_need_saving and creds: 
        try:
            with open(TOKEN_FILE, 'w') as token_file:
                token_file.write(creds.to_json())
            logger.info(f"Credentials saved to {TOKEN_FILE}")
        except Exception as e:
            logger.error(f"Error saving token to {TOKEN_FILE}: {e}")
            # If saving fails, current session might still proceed with 'creds'
            # but subsequent runs will have issues. For this script, we can proceed.

    # Final check for valid credentials
    if not creds or not creds.valid:
        logger.error("Failed to obtain valid credentials after all attempts.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service built successfully.")
        return service
    except HttpError as error:
        logger.error(f"An API error occurred while building the service: {error}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while building the service: {e}")
        return None

def fetch_inbox_emails(service):
    """Fetches all emails from the INBOX.
    Args:
        service: Authorized Gmail API service instance.
    Returns:
        list: A list of message IDs from the INBOX. Returns empty list on error.
    """
    logger.info("Fetching emails from INBOX...")
    message_ids = []
    try:
        # Initial request to get the first page of messages
        request = service.users().messages().list(userId='me', labelIds=['INBOX'])
        while request is not None:
            response = request.execute()
            messages = response.get('messages', [])
            if not messages:
                logger.info("No messages found in INBOX.")
                break
            
            current_page_ids = [msg['id'] for msg in messages]
            message_ids.extend(current_page_ids)
            logger.info(f"Fetched {len(current_page_ids)} email IDs from this page.")
            
            # Check if there's a next page
            request = service.users().messages().list_next(previous_request=request, previous_response=response)
        
        logger.info(f"Total email IDs fetched from INBOX: {len(message_ids)}")
        return message_ids
    except HttpError as error:
        logger.error(f"An API error occurred while fetching emails: {error}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching emails: {e}")
        return []

def archive_emails(service, message_ids):
    """Archives a list of emails by removing the INBOX label.
    Args:
        service: Authorized Gmail API service instance.
        message_ids (list): A list of email message IDs to archive.
    Returns:
        int: Count of successfully archived emails.
    """
    if not message_ids:
        logger.info("No emails to archive.")
        return 0

    logger.info(f"Starting to archive {len(message_ids)} emails...")
    archived_count = 0
    # Gmail API recommends batching requests if you're modifying many messages,
    # but for simplicity, we'll archive one by one here.
    # For larger volumes, consider using batch requests.
    # https://developers.google.com/gmail/api/guides/batch
    for i, message_id in enumerate(message_ids):
        try:
            # To archive, we remove the 'INBOX' label from the message.
            # Other labels (e.g., custom labels) will remain.
            # The 'UNREAD' label is also typically removed when archiving from INBOX,
            # but the primary action for "archiving" is removing INBOX.
            # If you specifically want to mark as read, add 'removeLabelIds': ['UNREAD']
            body = {'removeLabelIds': ['INBOX']}
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            archived_count += 1
            logger.info(f"Archived email {i+1}/{len(message_ids)} (ID: {message_id})")
        except HttpError as error:
            logger.error(f"API error archiving email ID {message_id}: {error}")
            # Optionally, decide if you want to stop or continue on error
        except Exception as e:
            logger.error(f"Unexpected error archiving email ID {message_id}: {e}")

    logger.info(f"Successfully archived {archived_count} out of {len(message_ids)} emails.")
    return archived_count

def main():
    """Main function to orchestrate email archiving."""
    logger.info("Gmail Archiver Script started.")
    
    service = authenticate_gmail()
    
    if not service:
        logger.error("Could not authenticate with Gmail. Exiting.")
        return

    inbox_message_ids = fetch_inbox_emails(service)
    
    if not inbox_message_ids:
        logger.info("No emails found in INBOX or an error occurred. Exiting.")
        return
        
    archive_emails(service, inbox_message_ids)
    
    logger.info("Gmail Archiver Script finished.")

if __name__ == '__main__':
    main()
    # To run this script:
    # 1. Make sure you have `credentials.json` in the same directory.
    # 2. Install necessary libraries:
    #    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    # 3. Run: python gmail_archiver.py
    #
    # The first time you run it, a browser window will open for you to authorize
    # the script to access your Gmail account. After successful authorization,
    # a `token.json` file will be created, storing your credentials for future runs.
    # Subsequent runs will use `token.json` and should not require browser interaction
    # unless the token expires or is revoked.
    #
    # Check gmail_archiver.log for detailed logs.
