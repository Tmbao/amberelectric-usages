"""Globird Electric Sensor definitions."""
from __future__ import annotations
from datetime import timedelta


import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    PLATFORM_SCHEMA,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .estimators import Last30DaysEstimator
from .globirds import GlobirdServiceClient, GlobirdDAO

DOMAIN = "globirdelectric"

_SCAN_INTERVAL = timedelta(minutes=5)

_CONF_ACCESS_TOKEN = "access_token"
_CONF_SITE = "site"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default="electric_smart_meter_sensor"): cv.string,
        vol.Required(_CONF_ACCESS_TOKEN): cv.string,
        vol.Required(_CONF_SITE): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    sensor_name = config.get(CONF_NAME)
    access_token = config.get(_CONF_ACCESS_TOKEN)
    site_id = config.get(_CONF_SITE)

    auth = GlobirdServiceClient.authenticate(access_token, site_id)
    globird_dao = GlobirdDAO(auth, Last30DaysEstimator())

    add_entities([GlobirdElectricSensor(sensor_name, globird_dao)])


class GlobirdElectricSensor(SensorEntity):
    def __init__(
        self,
        sensor_name: str,
        globird_dao: GlobirdDAO,
    ) -> None:
        self._attr_name = sensor_name
        self.globird_dao = globird_dao
        self._attr_device_class = DEVICE_CLASS_ENERGY
        self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        self._attr_native_unit_of_measurement = "kWh"

    @Throttle(_SCAN_INTERVAL)
    def update(self):
        now = dt_util.as_local(dt_util.now())
        self._attr_native_value = self.globird_dao.fetch(now)
