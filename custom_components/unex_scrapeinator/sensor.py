''' Sensor for the UnexScrapeinator integration '''

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
import homeassistant.util.dt

from .const import (DOMAIN, CONF_UPDATE_INTERVAL, CONF_CLIENT, CONF_PLATFORM)


_LOGGER: logging.Logger = logging.getLogger(f"custom_components.{DOMAIN}")


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    update_interval = hass.data[DOMAIN][CONF_UPDATE_INTERVAL] * 60

    async def async_update_data():
        await hass.async_add_executor_job(hass.data[DOMAIN][CONF_CLIENT].run)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=CONF_PLATFORM,
        update_method=async_update_data,
        update_interval=timedelta(minutes=update_interval),
    )

    await coordinator.async_request_refresh()

    async_add_entities([UnexScrapeinatorSensor(hass, coordinator)])


class UnexScrapeinatorSensor(SensorEntity):
    ''' Sensor for the UnexScrapeinator integration '''

    def __init__(self, hass, coordinator) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._icon = "mdi:email-multiple-outline"
        # self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_state_class = None

    @property
    def icon(self):
        return self._icon

    @property
    def extra_state_attributes(self):
        return {
            'posts': self.hass.data[DOMAIN][CONF_CLIENT].posts,
            'next_post': self.hass.data[DOMAIN][CONF_CLIENT].next_post
        }

    @property
    def unique_id(self):
        return ""

    @property
    def device_class(self):
        return SensorDeviceClass.DATE

    @property
    def state_class(self) -> str:
        """Return the state class of the sensor."""
        return self._attr_state_class

    @property
    def native_value(self) -> StateType:
        return homeassistant.util.dt.now()

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.last_update_success

    async def async_update(self):
        """Update the entity. Only used by the generic entity update service."""
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
