#!/bin/env python
""" This script runs the UnexScraper class. """


import logging
from datetime import datetime, time, timedelta
import locale
import os
from typing import Optional
import holidays
from unex_scrapeinator import UnexScrapeinator
from google_calendar import GoogleCalendar
from app_config import AppConfig


logger: logging.Logger = logging.getLogger("UnexScrapinator")
logging.basicConfig(level=logging.INFO)


class UnexCalendarinatorApp:
    """ This class is used to run the UnexScrapeinator class. """

    cfg: AppConfig
    _scraper: Optional[UnexScrapeinator] = None
    _calendar: Optional[GoogleCalendar] = None
    timezone: str
    calendar_events: list[dict]
    holiday_list: holidays.HolidayBase

    def __init__(self, config_dir: str):

        self.config_dir = config_dir

        self.cfg = AppConfig(
            config_file=os.path.join(self.config_dir, 'settings.yaml')
        )

        self.timezone = self.cfg.get('timezone')
        locale.setlocale(locale.LC_TIME, self.cfg.get('locale'))
        if self.cfg.get('holidays'):
            self.holiday_list = holidays.country_holidays(
                country=self.cfg.get('country')
            )

    def main(self):
        """ This method is the main entry point of the application. """

        self.calendar.delete_past_events()

        self.calendar_events = self.calendar.get_upcoming_events(
            num_events=100)

        self.scraper.run()

        self.process_and_posts_to_calendar()

        self.purge_unmatched_events()

    def process_and_posts_to_calendar(self):
        """ Process the scraper posts and add them to the calendar. """

        # Process the posts and add them to the calendar
        now = datetime.now()
        current_weekday = now.weekday()
        current_time = now.time()
        post_window_start = time(self.cfg.get('post_window.start'), 0)
        post_window_end = time(self.cfg.get('post_window.end'), 0)

        for post in self.scraper.posts:
            post_deadline = datetime.combine(
                post.posting_date, post_window_end
            )

            # Calculate the actual posting date based on the current date and time
            # If the desired posting date is in the past, calculate the next posting day
            if post_deadline < now:
                logger.debug("Posting date is in the past")
                days_until_next_posting_day = (
                    post.posting_date.weekday() - current_weekday + 7) % 7

                if days_until_next_posting_day == 0 and current_time > post_window_end:
                    days_until_next_posting_day = 7

                actual_posting_date = datetime.now() + timedelta(days=days_until_next_posting_day)
            else:
                actual_posting_date = post.posting_date

            # Calculate the posting intervals based on the actual posting date
            post_intervals = tuple([
                datetime.combine(self.previous_working_day(
                    actual_posting_date), post_window_start
                ),
                datetime.combine(
                    actual_posting_date, post_window_end
                )
            ])

            event = self.format_event(post, post_intervals)

            # Add the event to the calendar if it is not already present
            # (Determined by searching for the item ID in the events descriptions)
            if not any(
                e for e in self.calendar_events if f"ID: {post.item_id}" in e['description']
            ):
                self.calendar.add_event(event)

    def format_event(self, post, post_intervals):
        """ Format a calendar event from a post object

        Args:
            post (UnexSendItem): The post object
            post_intervals (tuple): The start and end intervals of the post sending window

        Returns:
            dict: The formatted calendar event.

        """
        event = {
            'summary': (
                ('📦' if post.sending_method == 'Post Office' else '✉️')
                + f" {post.receiver_name} (" +
                post.posting_date.strftime('%a').capitalize()
                + ")"
            ),
            'description':
            f"Afsendelsesmetode: {post.sending_method}\n" +
            f"Ønsket afsendelsesdato: {post.posting_date.strftime('%a %Y-%m-%d')}\n" +
            f"ID: {post.item_id}\n",
                'start': {
                    'dateTime': post_intervals[0].isoformat(),
                    'timeZone': self.timezone,
            },
            'end': {
                    'dateTime': post_intervals[1].isoformat(),
                    'timeZone': self.timezone,
            },
            'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 330},
                    ],
            },
            'transparency': 'transparent'
        }

        return event

    def purge_unmatched_events(self):
        """ Purge calendar events not present in the scrape results """

        for event in self.calendar_events:
            if not any(p for p in self.scraper.posts if f"ID: {p.item_id}" in event['description']):
                logger.info(
                    'Delete event: [%s] %s', event['start']['dateTime'], event['summary']
                )
                self.calendar.delete_event(event['id'])

    @property
    def calendar(self):
        """ Get the calendar object.

        Returns:
            GoogleCalendar: The calendar object.

        """
        if not self._calendar:
            calendar_id = self.cfg.get('calendar.id')
            self._calendar = GoogleCalendar(
                calendar_id=calendar_id,
                timezone=self.timezone,
                config_dir=self.config_dir
            )
        return self._calendar

    @property
    def scraper(self):
        """ Get the scraper object.

        Returns:
            UnexScrapeinator: The scraper object.

        """

        if not self._scraper:
            username = self.cfg.get('scraper.username')
            password = self.cfg.get('scraper.password')
            base_url = self.cfg.get('scraper.base_url')

            self._scraper = UnexScrapeinator(
                username=username, password=password, base_url=base_url
            )

        return self._scraper

    def previous_working_day(self, date):
        """ Get the previous working day from a given date

        Args:
            date (datetime): The date to get the previous working day from.

        Returns:
            datetime: The previous working day.

        """

        # Backtrack until not in a weekend or on a holiday
        while True:
            date -= timedelta(days=1)

            if date.weekday() >= 5:
                logger.debug(
                    "%s is in a weekend",
                    date.strftime('%a')
                )
                # continue
            elif self.cfg.get('holidays') and date in self.holiday_list:
                logger.debug("%s is a holiday (%s)", date.strftime(
                    '%a %Y-%m-%d'), self.holiday_list[date])
            else:
                logger.debug(
                    "%s is a working day", date.strftime('%a %Y-%m-%d')
                )
                return date


if __name__ == "__main__":

    app = UnexCalendarinatorApp(
        config_dir=os.path.realpath(
            os.path.expanduser(
                "~/.config/unex_calendarinator"
            )
        )
    )
    app.main()
