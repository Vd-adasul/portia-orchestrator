# api/tools/communication.py
import os
import json
import base64
from email.mime.text import MIMEText
from portia_sdk.tool import Tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- API KEY USAGE ---
# This file uses the following environment variables:
# - SLACK_BOT_TOKEN: For connecting to Slack.
# - GOOGLE_CREDENTIALS_JSON: For authenticating with Google.
# - GOOGLE_TOKEN_JSON: For authenticating with Google.

# --- Slack API Setup ---
try:
    slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    bot_info = slack_client.auth_test()
    SLACK_BOT_USER_ID = bot_info["user_id"]
except Exception as e:
    print(f"Error initializing Slack client: {e}")
    slack_client = None
    SLACK_BOT_USER_ID = None

# --- Gmail API Setup ---
def get_gmail_service():
    creds = None
    try:
        token_json = os.environ.get('GOOGLE_TOKEN_JSON')
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not token_json or not creds_json: return None
        creds = Credentials.from_authorized_user_info(json.loads(token_json), ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send'])
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"Error initializing Gmail service: {e}")
        return None
gmail_service = get_gmail_service()

# --- Live Tools ---
def fetch_unread_emails_func():
    if not gmail_service: return "Gmail service not available."
    try:
        results = gmail_service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=5).execute()
        messages = results.get('messages', [])
        emails = []
        for msg in messages:
            msg_data = gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            emails.append({"id": msg['id'], "from": sender, "subject": subject, "body": msg_data['snippet']})
        return emails
    except HttpError as error: return f"An error occurred with Gmail API: {error}"

def fetch_slack_messages_func():
    if not slack_client or not SLACK_BOT_USER_ID: return "Slack client not available."
    try:
        response = slack_client.search_messages(query=f"<@{SLACK_BOT_USER_ID}>", count=5)
        return [{"id": m.get('ts'), "user": m.get('user'), "channel": m.get('channel', {}).get('id'), "text": m.get('text')} for m in response['messages']['matches']]
    except SlackApiError as e: return f"An error occurred with Slack API: {e.response['error']}"

def send_gmail_reply_func(thread_id: str, body: str):
    if not gmail_service: return "Gmail service not available."
    try:
        thread = gmail_service.users().threads().get(userId='me', id=thread_id).execute()
        headers = thread['messages'][0]['payload']['headers']
        subject = next(h['value'] for h in headers if h['name'] == 'Subject')
        to_address = next(h['value'] for h in headers if h['name'] == 'From')
        message = MIMEText(body)
        message['to'], message['subject'] = to_address, f"Re: {subject}"
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        gmail_service.users().messages().send(userId='me', body={'raw': raw_message, 'threadId': thread_id}).execute()
        return f"Successfully sent reply to thread {thread_id}."
    except HttpError as error: return f"An error occurred sending Gmail reply: {error}"

def send_slack_message_func(channel_id: str, message: str):
    if not slack_client: return "Slack client not available."
    try:
        slack_client.chat_postMessage(channel=channel_id, text=message)
        return f"Successfully sent message to {channel_id}."
    except SlackApiError as e: return f"An error occurred sending Slack message: {e.response['error']}"

# --- Tool Definitions ---
fetch_unread_emails = Tool(id="fetch_unread_emails", func=fetch_unread_emails_func, description="Fetches a list of the latest unread emails.")
fetch_slack_messages = Tool(id="fetch_slack_messages", func=fetch_slack_messages_func, description="Fetches a list of the latest Slack messages mentioning me.")
send_gmail_reply = Tool(id="send_gmail_reply", func=send_gmail_reply_func, description="Sends a reply to a given Gmail email thread ID.")
send_slack_message = Tool(id="send_slack_message", func=send_slack_message_func, description="Sends a message to a given Slack channel or user ID.")
communication_tools = [fetch_unread_emails, fetch_slack_messages, send_gmail_reply, send_slack_message]