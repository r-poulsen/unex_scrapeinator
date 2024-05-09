#!/bin/env python

import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz


# If modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/calendar']
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

SCOPES = ["https://www.googleapis.com/auth/calendar.events.owned"]

# "https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendar:
    def __init__(self, calendar_id: str = 'primary'):
        self.creds = None
        self.service = None
        self.calendar_id = calendar_id
        self._authenticate()

    def _authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file(
                'token.json', SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('token.json', 'w', encoding='utf-8') as token:
                token.write(self.creds.to_json())

        self.service = build(
            'calendar', 'v3', credentials=self.creds,
            cache_discovery=False
        )

    def get_upcoming_events(self, num_events=10):
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        # print('Getting the upcoming {} events'.format(num_events))

        events_result = self.service.events().list(
            calendarId=self.calendar_id, timeMin=now,
            maxResults=num_events, singleEvents=True,
            orderBy='startTime').execute()
        return events_result.get('items', [])

    def add_event(self, event):
        event = self.service.events().insert(
            calendarId=self.calendar_id, body=event).execute()
        print('Event created: {}'.format(event.get('htmlLink')))
        return event

    def delete_past_events(self):

        tz = pytz.timezone('Europe/Copenhagen')  # replace with your timezone

        # now = datetime.datetime.utcnow().isoformat() + 'Z'
        # print(f"{now=}")
        now = datetime.datetime.now(tz=tz).strftime(
            '%Y-%m-%dT%H:%M:%S%z')
        # print(f"{now=}")
        past_events = self.service.events().list(
            calendarId=self.calendar_id, timeMax=now,
            singleEvents=True, orderBy='startTime').execute()
        for event in past_events.get('items', []):
            event_end_time = datetime.datetime.fromisoformat(
                event['end']['dateTime'].rstrip('Z'))
            if event_end_time < datetime.datetime.now(tz=tz):
                self.service.events().delete(
                    calendarId=self.calendar_id,
                    eventId=event['id']).execute()
        # print('Past events deleted')


if __name__ == '__main__':
    calendar = GoogleCalendar(
        calendar_id='d1ba6c45f89f3f039abd9814ad4356e73575bc55f854ef8702916092821d9309@group.calendar.google.com'
    )

    print(calendar.get_upcoming_events())
    # event = {
    #     'summary': 'Test Event',
    #     'location': 'Somewhere',
    #     'description': 'This is a test event',
    #     'start': {
    #         'dateTime': '2021-09-01T09:00:00',
    #         'timeZone': 'America/Los_Angeles',
    #     },
    #     'end': {
    #         'dateTime': '2021-09-01T17:00:00',
    #         'timeZone': 'America/Los_Angeles',
    #     },
    #     'recurrence': [
    #         'RRULE:FREQ=DAILY;COUNT=2'
    #     ],
    #     'attendees': [
    #         {'email': 'test@test.com'},
    #     ],
    #     'reminders': {
    #         'useDefault': False,
    #         'overrides': [
    #             {'method': 'email', 'minutes': 24 * 60},
    #             {'method': 'popup', 'minutes': 10},
    #         ],
    #     },
    # }
    # calendar.add_event(event)
    calendar.delete_past_events()
