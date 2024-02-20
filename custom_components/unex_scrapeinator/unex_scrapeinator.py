''' This module is used to scrape the UNEX website. '''

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from requests_html import HTMLSession

from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(f"custom_components.{DOMAIN}")


class ScrapeinatorException(Exception):
    """ This class is used to raise exceptions in the Scrapeinator class. """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class UnexSendItem:
    """ This class is used to store the data of a sending item. """
    item_id: str
    receiver_name: str
    sending_method: str
    requested_posting_date: datetime | str
    actual_posting_date: datetime = field(init=False)

    def __post_init__(self) -> None:

        self.requested_posting_date = datetime.strptime(
            self.requested_posting_date.split(' ')[0], '%Y%m%d'
        ).date()

        today = date.today()
        if self.requested_posting_date < today:
            days_difference = (today - self.requested_posting_date).days
            weeks_difference = days_difference // 7
            next_date = self.requested_posting_date + \
                timedelta(weeks=weeks_difference + 1)
            if next_date < today:
                next_date += timedelta(weeks=1)

            self.actual_posting_date = next_date
        else:
            self.actual_posting_date = self.requested_posting_date

    def __repr__(self) -> str:
        return (
            "UnexSendItem(" +
            f"{self.item_id}, {self.receiver_name}, " +
            f"{self.sending_method}, {self.requested_posting_date}" +
            ")"
        )

    def __str__(self) -> str:
        return (
            f"Item ID: {self.item_id}\n" +
            f"Receiver Name: {self.receiver_name}\n" +
            f"Sending Method: {self.sending_method}\n" +
            f"Date: {self.requested_posting_date}"
        )


class UnexScrapeinator:
    """ This class is used to scrape the UNEX website. """
    posts: list[datetime, list[UnexSendItem]] = []
    next_post: tuple[datetime, list[UnexSendItem]]

    def __init__(self, **kwargs) -> None:
        _LOGGER.debug("UnexScrapeinator.__init__")
        self.__username = kwargs.get("username")
        self.__password = kwargs.get("password")

        self.__urls = {
            'login': kwargs.get("base_url") + "j_spring_security_check",
            'posting_plan': kwargs.get("base_url") + "dataentry/overview/send.htm"
        }
        self.__session = HTMLSession()
        self.__session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        })

    def __login(self) -> None:
        """ This method logs into the UNEX website. """
        _LOGGER.debug("UnexScrapeinator.__login")
        login_payload = {
            "j_username": self.__username,
            "j_password": self.__password,
            "token": ""
        }
        response = self.__session.post(
            self.__urls['login'], data=login_payload)

        response.raise_for_status()

        jsessionid = response.cookies['JSESSIONID']
        self.__session.headers.update(
            {"Cookie": f"JSESSIONID={jsessionid}"}
        )

    def run(self) -> None:
        """ This method runs the scraper """
        _LOGGER.debug("UnexScrapeinator.run")

        # If we don't have a session cookie, we need to login
        if self.__session.cookies.get('JSESSIONID') is None:
            self.__login()

        response = self.__session.get(self.__urls['posting_plan'])
        response.raise_for_status()

        posts_dict = {}
        self.posts = []

        # If we're redirected to the login page, the session cookie probably expired
        # and we need to login again.
        if response.html.find('title', first=True).text == "Panel Zone | Sign In":
            self.__login()
            response = self.__session.get(self.__urls['posting_plan'])
            response.raise_for_status()

        # At this point we should have reached the overview page or something went wrong
        if not response.html.find('title', first=True).text.startswith("Panel Zone | Posting plan"):
            raise ScrapeinatorException(
                f"Unexpected pagetitle: {
                    response.html.find('title', first=True).text}"
            )

        for row in response.html.find('tr')[1:]:
            send_item = UnexSendItem(*[c.text for c in row.find('td')][:4])

            if send_item.actual_posting_date.strftime(
                    "%Y-%m-%d") not in posts_dict:
                posts_dict[send_item.actual_posting_date.strftime(
                    "%Y-%m-%d")] = []

            posts_dict[send_item.actual_posting_date.strftime("%Y-%m-%d")].append({
                "id": send_item.item_id,
                "receiver_name": send_item.receiver_name,
                "sending_method": send_item.sending_method,
                "requested_posting_date": send_item.requested_posting_date.strftime("%Y-%m-%d"),
                "actual_posting_date": send_item.actual_posting_date.strftime("%Y-%m-%d")
            })

        for k, v in sorted(posts_dict.items()):
            self.posts.append([k, v])

        self.next_post = (self.posts[0][0], self.posts[0][1])
