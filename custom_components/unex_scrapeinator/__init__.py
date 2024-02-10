import logging
from homeassistant import core

from .unex_scrapeinator import UnexScrapeinator

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_CLIENT,
    UPDATE_INTERVAL, CONF_PLATFORM
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the UNEX Scrapeinator component."""
    # @TODO: Add setup code.

    conf = config.get(DOMAIN)
    # If no config, abort
    if conf is None:
        return True

    hass.data[DOMAIN] = {
        CONF_CLIENT: UnexScrapeinator(
            username=conf.get("username"),
            password=conf.get("password"),
            base_url=conf.get("base_url")),
        CONF_UPDATE_INTERVAL: conf.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL)
    }

    hass.async_create_task(
        hass.helpers.discovery.async_load_platform(
            CONF_PLATFORM, DOMAIN, conf, config)
    )

    return True
