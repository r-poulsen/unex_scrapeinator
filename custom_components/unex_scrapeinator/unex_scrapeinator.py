''' This module is used to scrape the UNEX website. '''

import logging
from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from urllib.parse import urljoin
from requests_html import HTMLSession, HTMLResponse, Element
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime


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
    requested_posting_date: date | str
    actual_posting_date: date = field(init=False)
    posting_intervals: tuple[tuple[datetime, datetime],
                             tuple[datetime, datetime]] = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.requested_posting_date, str):
            self.requested_posting_date = datetime.strptime(
                self.requested_posting_date.split(' ')[0], '%Y%m%d'
            ).date()

        now = datetime.now()
        requested_posting_datetime = datetime.combine(
            self.requested_posting_date, time(10, 0))

        # TODO This doesn't check for holidays

        # Get the next same weekday
        next_same_weekday = datetime.now(
        ) + relativedelta(weekday=self.requested_posting_date.weekday())

        if now > requested_posting_datetime:
            # If current time has passed 10:00 on the requested_posting_date,
            # set actual_posting_date to the next same weekday
            self.actual_posting_date = next_same_weekday
        else:
            # If current time hasn't passed 10:00 on the requested_posting_date,
            # set actual_posting_date to the requested_posting_date
            self.actual_posting_date = self.requested_posting_date

        previous_workday = self.get_previous_workday(self.actual_posting_date)
        start_time = datetime.combine(previous_workday, time(10, 0))
        end_time = datetime.combine(self.actual_posting_date, time(10, 0))

        # TODO This just adds one week and does not take holidays into account
        self.posting_intervals = (
            (start_time, end_time),
            (
                start_time +
                timedelta(weeks=1),
                end_time + timedelta(weeks=1)
            )
        )

    @staticmethod
    def get_previous_workday(input_date):
        """ This method returns the previous workday of the input date.

        Args:
            input_date (date): The input date.

        Returns:
            date: The previous workday of the input date.
        """

        # TODO Does not take holidays into account
        previous_workday = input_date - timedelta(days=1)
        while previous_workday.weekday() > 4:  # 0-4 corresponds to Monday - Friday
            previous_workday -= timedelta(days=1)
        return previous_workday

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
    posts: list[tuple[datetime, list[UnexSendItem]]] = []
    next_post: tuple[datetime, list[UnexSendItem]]
    __session: HTMLSession

    def __init__(self, **kwargs) -> None:
        _LOGGER.debug("UnexScrapeinator.__init__")
        self.__username = kwargs.get("username")
        self.__password = kwargs.get("password")

        base_url = kwargs.get("base_url")
        if isinstance(base_url, str):
            self.__urls = {
                'login': urljoin(base_url, "j_spring_security_check"),
                'posting_plan': urljoin(base_url, "dataentry/overview/send.htm")
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

        response = self.__session.get(
            self.__urls['posting_plan'])
        assert isinstance(response, HTMLResponse)
        response.raise_for_status()

        posts_dict = {}
        self.posts = []

        # If we're redirected to the login page, the session cookie probably expired
        # and we need to login again.

        title_element = response.html.find('title', first=True)
        assert isinstance(title_element, Element)
        if title_element.text == "Panel Zone | Sign In":
            self.__login()
            response = self.__session.get(self.__urls['posting_plan'])
            assert isinstance(response, HTMLResponse)
            response.raise_for_status()

        # At this point we should have reached the overview page or something went wrong

        title_element = response.html.find('title', first=True)
        assert isinstance(title_element, Element)
        if not title_element.text.startswith("Panel Zone | Posting plan"):
            raise ScrapeinatorException(
                f"Unexpected pagetitle: {title_element.text}"
            )

        row_elements = response.html.find('tr')
        assert isinstance(row_elements, list)
        for row in row_elements[1:]:
            td_elements = row.find('td')
            assert isinstance(td_elements, list)
            send_item = UnexSendItem(*[c.text for c in td_elements][:4])

            if send_item.actual_posting_date.strftime(
                    "%Y-%m-%d") not in posts_dict:
                posts_dict[send_item.actual_posting_date.strftime(
                    "%Y-%m-%d")] = []

            assert isinstance(send_item.requested_posting_date, date)
            posts_dict[send_item.actual_posting_date.strftime("%Y-%m-%d")].append({
                "id": send_item.item_id,
                "receiver_name": send_item.receiver_name,
                "sending_method": send_item.sending_method,
                "requested_posting_date": send_item.requested_posting_date.strftime("%Y-%m-%d"),
                "actual_posting_date": send_item.actual_posting_date.strftime("%Y-%m-%d"),
                "actual_posting_intervals": send_item.posting_intervals
            })

        for k, v in sorted(posts_dict.items()):
            self.posts.append((k, v))

        self.next_post = self.posts[0]
