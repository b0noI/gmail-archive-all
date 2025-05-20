# Gmail Archiver Script

## Description
This script connects to a Gmail account using OAuth 2.0, fetches all emails currently in the INBOX, and then archives them. Archived emails are removed from the INBOX view but remain accessible in "All Mail" and via Gmail search.

## Prerequisites
Before running this script, ensure you have the following:

1.  **Python 3.6+**: Download from [python.org](https://www.python.org/downloads/).
2.  **Google Cloud Platform (GCP) Project**:
    *   If you don't have one, create a project at [https://console.cloud.google.com/](https://console.cloud.google.com/).
3.  **Gmail API Enabled**:
    *   In your GCP project, navigate to "APIs & Services" > "Library".
    *   Search for "Gmail API" and enable it for your project.
4.  **OAuth 2.0 Credentials (`credentials.json`)**:
    *   **Configure OAuth Consent Screen**:
        *   In your GCP project, go to "APIs & Services" > "OAuth consent screen".
        *   Choose "External" as the user type (or "Internal" if you are part of a Google Workspace organization and the app is for internal use). Click "Create".
        *   Fill in the required application details (App name, User support email, Developer contact information).
        *   On the "Scopes" page, click "Add or Remove Scopes".
        *   Search for or manually input the scope: `https://www.googleapis.com/auth/gmail.modify`. Add it to your project.
        *   Continue through the consent screen setup, adding test users if your app is in "testing" mode (newly created external apps often start in testing mode).
        *   Ensure the consent screen is published or otherwise usable by your account.
    *   **Create OAuth Client ID**:
        *   Navigate to "APIs & Services" > "Credentials".
        *   Click "+ CREATE CREDENTIALS" at the top and select "OAuth client ID".
        *   Choose "Desktop app" as the Application type.
        *   Give it a name (e.g., "Gmail Archiver Script Client").
        *   Click "CREATE".
        *   A dialog will show your Client ID and Client secret. Click "DOWNLOAD JSON" to download the credentials file.
        *   **Rename the downloaded JSON file to `credentials.json`**.
        *   **Place this `credentials.json` file in the same directory as the `gmail_archiver.py` script.**

## Setup Instructions

1.  **Clone the Repository / Download Files**:
    *   If this is a Git repository: `git clone <repository_url>`
    *   Alternatively, download `gmail_archiver.py`, `test_gmail_archiver.py`, and `requirements.txt` into the same directory.

2.  **Install Required Libraries**:
    *   Open a terminal or command prompt in the script's directory.
    *   Install the necessary Python packages using pip and the `requirements.txt` file:
        ```bash
        pip install -r requirements.txt
        ```
    *   The `requirements.txt` file specifies the following libraries:
        *   `google-api-python-client`: The Google API Client Library for Python.
        *   `google-auth-httplib2`: The Google Authentication Library for Python using httplib2.
        *   `google-auth-oauthlib`: The Google Authentication Library for Python using OAuthlib for user authorization.

## Running the Script

1.  **Execute the Script**:
    *   Open a terminal or command prompt in the script's directory.
    *   Run the script using:
        ```bash
        python gmail_archiver.py
        ```

2.  **First-Time Authorization**:
    *   The first time you run the script, a web browser window will automatically open.
    *   You will be prompted to log in to your Google account and then grant the script permission to "Read, compose, send, and permanently delete all your email from Gmail" (this is what the `gmail.modify` scope enables, which is necessary for reading and archiving).
    *   After successful authorization, the script will proceed.

3.  **`token.json` Creation**:
    *   Upon successful first-time authorization, a file named `token.json` will be created in the same directory.
    *   This file stores your OAuth 2.0 access and refresh tokens, allowing the script to run on subsequent occasions without requiring browser authorization each time.
    *   **Important**: Keep this file secure.

4.  **Logging**:
    *   The script logs its operations and any errors to a file named `gmail_archiver.log`.
    *   Logs are also printed to the console in real-time.

## Running Tests
The project includes a suite of unit tests to ensure the script's components function correctly. These tests mock external API calls and file system operations, so **they do not affect your actual Gmail account or local files like `token.json`**.

1.  **Execute Tests**:
    *   Open a terminal or command prompt in the script's directory.
    *   Run the tests using:
        ```bash
        python -m unittest test_gmail_archiver.py
        ```

## Important Notes/Warnings

*   **Archiving is a Modification**: Archiving emails removes them from your inbox. While they are not deleted and can still be found in "All Mail" and through Gmail's search functionality, your inbox view will change.
*   **Rate Limits**: For users with exceptionally large inboxes (many thousands of emails), the script might approach or exceed Google's Gmail API rate limits. The script currently archives emails one by one. If rate limit issues occur, you might need to run the script multiple times or adapt it for batch processing (which is more complex).
*   **Security**:
    *   The `credentials.json` file contains sensitive information that allows the script to request access to your Gmail account.
    *   The `token.json` file contains active tokens that grant the script access to your Gmail account as per the authorized scopes.
    *   **Keep both `credentials.json` and `token.json` files secure and private.** Do not share them or commit them to public version control repositories. If you suspect they are compromised, revoke the script's access from your Google Account settings ([https://myaccount.google.com/permissions](https://myaccount.google.com/permissions)) and delete the `token.json` file. You may also need to delete and recreate your OAuth 2.0 client ID in the GCP console.

## Troubleshooting

*   **`credentials.json not found`**:
    *   Ensure you have downloaded the OAuth 2.0 client ID JSON file from the GCP Console.
    *   Make sure it is renamed to exactly `credentials.json`.
    *   Confirm that `credentials.json` is in the same directory as `gmail_archiver.py`.
*   **Authorization Errors / Scope Issues (e.g., `Error 403: access_denied` or similar during login)**:
    *   Double-check that the Gmail API is enabled in your GCP project.
    *   Verify that your OAuth Consent Screen is correctly configured and that you have added the `https.www.googleapis.com/auth/gmail.modify` scope.
    *   If your GCP app is in "testing" mode, ensure the Google account you're trying to authenticate with is listed as a "Test user" in the OAuth consent screen configuration.
*   **`ModuleNotFoundError`**:
    *   Ensure you have installed the required libraries by running `pip install -r requirements.txt`.
*   **`HttpError ... "rateLimitExceeded"`**:
    *   You've made too many API requests in a short period. Wait for some time (e.g., a few hours or a day) and try running the script again. For very large inboxes, this might require multiple runs.
*   **Token Issues (`token.json`)**:
    *   If you encounter persistent authentication problems even with `token.json` present, try deleting `token.json` and re-running the script to go through the browser authorization flow again. This can resolve issues with corrupted or revoked tokens.
