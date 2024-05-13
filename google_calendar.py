#!/bin/env python
""" This module is used to interact with the Google Calendar API. """

import datetime
import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

logger: logging.Logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events.owned"]


class GoogleCalendar:
    """ This class is used to interact with the Google Calendar API. """

    def __init__(self, calendar_id: str = 'primary', timezone='UTC', config_dir: str = ''):
        self.creds = None
        self.service = None
        self.calendar_id = calendar_id
        self.timezone = pytz.timezone(timezone)
        self.config_dir = config_dir

        self.token_file = os.path.join(self.config_dir, 'token.json')
        self.cred_file = os.path.join(self.config_dir, 'credentials.json')

        self._authenticate()

    def _authenticate(self):
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(
                self.token_file, SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.cred_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(self.token_file, 'w', encoding='utf-8') as token:
                token.write(self.creds.to_json())

        self.service = build(
            'calendar', 'v3', credentials=self.creds,
            cache_discovery=False
        )

    def get_upcoming_events(self, num_events=10):
        """ Call the Calendar API to get the upcoming events.

        Args:
            num_events (int): The number of upcoming events to retrieve.

        Returns:
            list: A list of the upcoming events.
        """
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        # print('Getting the upcoming {} events'.format(num_events))

        events_result = self.service.events().list(
            calendarId=self.calendar_id, timeMin=now,
            maxResults=num_events, singleEvents=True,
            orderBy='startTime').execute()
        return events_result.get('items', [])

    def add_event(self, event):
        """ Add an event to the calendar.

        Args:
            event (dict): The event to add.

        Returns:
            dict: The added event.
        """

        event = self.service.events().insert(
            calendarId=self.calendar_id, body=event).execute()
        logger.info(
            'Event added: [%s] %s', event['start']['dateTime'], event['summary']
        )
        return event

    def delete_past_events(self):
        """ Delete past events from the calendar. """

        now = datetime.datetime.now(tz=self.timezone).strftime(
            '%Y-%m-%dT%H:%M:%S%z')
        past_events = self.service.events().list(
            calendarId=self.calendar_id, timeMax=now,
            singleEvents=True, orderBy='startTime').execute()
        for event in past_events.get('items', []):
            event_end_time = datetime.datetime.fromisoformat(
                event['end']['dateTime'].rstrip('Z'))
            if event_end_time < datetime.datetime.now(tz=self.timezone):
                self.delete_event(event['id'])

    def delete_event(self, event_id):
        """ Delete an event from the calendar.

        Args:
            event_id (str): The ID of the event to delete.

        """

        self.service.events().delete(
            calendarId=self.calendar_id, eventId=event_id).execute()
        logger.debug('Event deleted: %s', event_id)


if __name__ == '__main__':
    calendar = GoogleCalendar(calendar_id='primary')
    print(calendar.get_upcoming_events())
