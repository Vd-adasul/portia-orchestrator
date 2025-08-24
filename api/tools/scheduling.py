# api/tools/scheduling.py
import os
import json
from datetime import datetime, timedelta, timezone
from portia_sdk.tool import Tool
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- API KEY USAGE ---
# This file uses the following environment variables:
# - GOOGLE_CREDENTIALS_JSON: For authenticating with Google.
# - GOOGLE_TOKEN_JSON: For authenticating with Google.

# --- Google Calendar API Setup ---
def get_calendar_service():
    creds = None
    try:
        token_json = os.environ.get('GOOGLE_TOKEN_JSON')
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not token_json or not creds_json: return None
        creds = Credentials.from_authorized_user_info(json.loads(token_json), ['https://www.googleapis.com/auth/calendar'])
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error initializing Calendar service: {e}")
        return None
calendar_service = get_calendar_service()

# --- Live Tool ---
def schedule_meeting_func(title: str, duration_minutes: int, attendees: list = None):
    if not calendar_service: return "Calendar service not available."
    try:
        now = datetime.now(timezone.utc)
        freebusy_response = calendar_service.freebusy().query(body={
            "timeMin": now.isoformat(), "timeMax": (now + timedelta(days=7)).isoformat(), "items": [{"id": "primary"}]
        }).execute()
        busy_slots = freebusy_response['calendars']['primary']['busy']
        start_time = now
        while True:
            end_time = start_time + timedelta(minutes=duration_minutes)
            is_free = all(max(start_time, datetime.fromisoformat(b['start'].replace('Z', '+00:00'))) >= min(end_time, datetime.fromisoformat(b['end'].replace('Z', '+00:00'))) for b in busy_slots)
            if is_free: break
            conflicting_slots = [b for b in busy_slots if datetime.fromisoformat(b['start'].replace('Z', '+00:00')) < end_time]
            if not conflicting_slots: break
            start_time = max(datetime.fromisoformat(b['end'].replace('Z', '+00:00')) for b in conflicting_slots)

        event_body = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': (start_time + timedelta(minutes=duration_minutes)).isoformat(), 'timeZone': 'UTC'},
            'attendees': [{'email': email} for email in attendees] if attendees else []
        }
        created_event = calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Successfully scheduled '{title}' at {start_time.strftime('%H:%M')} UTC. Link: {created_event.get('htmlLink')}"
    except HttpError as error: return f"An error occurred with Google Calendar API: {error}"

# --- Tool Definition ---
schedule_meeting = Tool(id="schedule_meeting", func=schedule_meeting_func, description="Schedules a meeting in the user's primary Google Calendar at the next available time slot.")
scheduling_tools = [schedule_meeting]
