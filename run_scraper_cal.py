#!/bin/env python
""" This script runs the UnexScraper class. """


import logging
from datetime import datetime, time, timedelta
import yaml
from custom_components.unex_scrapeinator import UnexScrapeinator
from custom_components.unex_scrapeinator.const import DOMAIN
from google_calendar import GoogleCalendar

logger: logging.Logger = logging.getLogger(DOMAIN)
logging.basicConfig(level=logging.INFO)
# logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


def previous_working_day(date):
    """ Get the previous working day.
    Args:
        date (datetime): The date to get the previous working day from.
    Returns:
        datetime: The previous working day.
    """

    while True:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            return date


if __name__ == "__main__":
    with open('secret.yaml', 'r', encoding="utf-8") as file:
        config = yaml.safe_load(file)

    username = config['username']
    password = config['password']
    base_url = config['base_url']
    calendar_id = config['calendar_id']

    scraper = UnexScrapeinator(
        username=username, password=password, base_url=base_url
    )

    c = GoogleCalendar(
        calendar_id=calendar_id
    )

    c.delete_past_events()

    events = c.get_upcoming_events(num_events=100)

    scraper.run()

    now = datetime.now()

    for p in scraper.posts:

        post_deadline = datetime.combine(
            p.posting_date, time(10, 0)
        )
        posting_date_weekday = p.posting_date.weekday()
        today = datetime.now().date()
        today_weekday = today.weekday()

        if post_deadline < now:
            logger.debug("Posting date is in the past")

            days_until_next_posting_day = (
                p.posting_date.weekday() - datetime.now().weekday() + 7) % 7

            if days_until_next_posting_day == 0:
                days_until_next_posting_day = 7

            actual_posting_date = datetime.now() + timedelta(days=days_until_next_posting_day)
        else:
            actual_posting_date = p.posting_date

        post_intervals = tuple([
            datetime.combine(previous_working_day(
                actual_posting_date), time(12, 0)),
            datetime.combine(actual_posting_date, time(10, 0))
        ]
        )

        logger.debug(p)
        logger.debug(post_intervals)

        event = {
            'summary': f"{'📦' if p.sending_method == 'Post Office' else '✉️'} {p.receiver_name}",
            'description': f"""Afsendelsesmetode: {p.sending_method}
Ønsket afsendelsesdato: {p.posting_date.strftime('%a %Y-%m-%d')}
ID: {p.item_id}""",
            'start': {
                'dateTime': post_intervals[0].isoformat(),
                'timeZone': 'Europe/Copenhagen',
            },
            'end': {
                'dateTime': post_intervals[1].isoformat(),
                'timeZone': 'Europe/Copenhagen',
            },

            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 330},
                ],
            },

            'transparency': 'transparent'
        }

        if not any(e for e in events if e['description'] == event['description']):
            c.add_event(event)
