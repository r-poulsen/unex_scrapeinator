''' This module is used to scrape the UNEX website. '''

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from requests_html import HTMLSession

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)


@dataclass
class UnexSendItem:
    """ This class is used to store the data of a sending item. """
    item_id: str
    receiver_name: str
    sending_method: str
    requested_posting_date: datetime | str
    actual_posting_date: datetime = field(init=False)

    # date needs to be converted to a timedate object from the string
    def __post_init__(self) -> None:
        self.requested_posting_date = self.requested_posting_date.split(' ')[0]
        self.requested_posting_date = datetime.strptime(self.requested_posting_date, '%Y%m%d')

        # date = datetime.strptime(posts[post]['date'], "%Y-%m-%d")

        today = datetime.now()
        if self.requested_posting_date < today:  # Check if the date is in the past
            # Calculate the difference in days between today and the past date
            days_difference = (today - self.requested_posting_date).days

            # Calculate the number of weeks that have passed since the past date
            weeks_difference = days_difference // 7

            # Calculate the next occurrence of the same weekday within the next week
            next_date = self.requested_posting_date + timedelta(weeks=weeks_difference + 1)

            # Adjust the next date if it's earlier than today
            if next_date < today:
                next_date += timedelta(weeks=1)

            self.actual_posting_date = next_date.date()

        else:
            self.requested_posting_date = self.requested_posting_date.date()
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
    # next_posts: dict[UnexSendItem] = {}
    next_post: (datetime, [UnexSendItem])

    def __init__(self, **kwargs) -> None:

        logging.warning("UnexScrapeinator.__init__")
        self.__username = kwargs.get("username")
        self.__password = kwargs.get("password")

        self.__urls = {
            'login': kwargs.get("base_url") + "j_spring_security_check",
            'posting_plan': kwargs.get("base_url") + "dataentry/overview/send.htm"
        }
        self.__session = HTMLSession()
        self.__session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
        )

    def __login(self) -> None:
        """ This method logs into the UNEX website. """
        login_payload = {
            "j_username": self.__username,
            "j_password": self.__password,
            "token": ""
        }
        response = self.__session.post(
            self.__urls['login'], data=login_payload)

        # Extract the JSESSIONID cookie from the response and add it to the session
        jsessionid = response.cookies['JSESSIONID']
        self.__session.headers.update(
            {"Cookie": f"JSESSIONID={jsessionid}"}
        )

    def run(self) -> None:
        """ This method runs the scraper """

        self.__login()
        response = self.__session.get(self.__urls['posting_plan'])

        posts_dict = {}
        for row in response.html.find('tr')[1:]:
            send_item = UnexSendItem(*[c.text for c in row.find('td')][:4])

            if send_item.actual_posting_date not in posts_dict:
                posts_dict[send_item.actual_posting_date.strftime("%Y-%m-%d")] = []

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
