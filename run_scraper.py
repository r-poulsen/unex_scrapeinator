#!/bin/env python
""" This script runs the UnexScraper class. """

from pprint import pprint
from time import sleep
import logging
import yaml
from custom_components.unex_scrapeinator import UnexScrapeinator
from custom_components.unex_scrapeinator.const import DOMAIN


_LOGGER: logging.Logger = logging.getLogger(DOMAIN)

logging.basicConfig(level=logging.DEBUG)

with open('secret.yaml', 'r', encoding="utf-8") as file:
    config = yaml.safe_load(file)

username = config['username']
password = config['password']
base_url = config['base_url']

scraper = UnexScrapeinator(
    username=username, password=password, base_url=base_url
)

scraper.run()
pprint(scraper.posts)
