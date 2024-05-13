''' This module is used to scrape the UNEX website. '''

import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

from pytz import timezone
from requests_html import Element, HTMLResponse, HTMLSession


_LOGGER: logging.Logger = logging.getLogger(__name__)


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
    _posting_date: str

    def __post_init__(self) -> None:
        self.posting_date = datetime.strptime(
            self._posting_date.split(' ')[0], '%Y%m%d'
        ).date()

    tz = timezone('Europe/Copenhagen')

    def __repr__(self) -> str:
        return (
            "UnexSendItem(" +
            f"{self.item_id}, {self.receiver_name}, " +
            f"{self.sending_method}, {self.posting_date}" +
            ")"
        )

    def __str__(self) -> str:
        return (
            f"Item ID: {self.item_id}\n" +
            f"Receiver Name: {self.receiver_name}\n" +
            f"Sending Method: {self.sending_method}\n" +
            f"Date: {self.posting_date}"
        )


class UnexScrapeinator:
    """ This class is used to scrape the UNEX website. """
    posts: list[UnexSendItem] = []
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
            self.posts.append(UnexSendItem(
                *[c.text for c in td_elements][:4]))
