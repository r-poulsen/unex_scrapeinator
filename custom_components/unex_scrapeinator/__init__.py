""" The UNEX Scrapeinator component. """

import logging
from homeassistant import core

from .unex_scrapeinator import UnexScrapeinator

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_CLIENT,
    UPDATE_INTERVAL, CONF_PLATFORM, SENSOR
)

_LOGGER = logging.getLogger(f"custom_components.{DOMAIN}")


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the UNEX Scrapeinator component."""

    async def handle_update(call):
        """Handle the service call."""
        # await hass.async_add_executor_job(hass.data[DOMAIN][CONF_CLIENT].run)
        # hass.data[DOMAIN][CONF_CLIENT].run()

        await hass.data[DOMAIN][SENSOR].coordinator.async_request_refresh()

    conf = config.get(DOMAIN)
    # If no config, abort
    if conf is None:
        return False

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

    hass.services.async_register(DOMAIN, "update", handle_update)

    return True
