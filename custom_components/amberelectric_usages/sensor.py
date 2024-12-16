"""Amber Electric - Usages Sensor definitions."""

# There is only one sensor that gives the latest time of usage data.
# The actual usage data will be written directly into statistics


from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AmberConfigEntry
from .const import ATTRIBUTION
from .coordinator import AmberUsagesCoordinator


class AmberUsagesLatestDataSensor(
    CoordinatorEntity[AmberUsagesCoordinator], SensorEntity
):
    """Amber usages latest data sensor."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: AmberUsagesCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator)
        self.site_id = coordinator.site_id
        self.entity_description = description

        self._attr_unique_id = f"{self.site_id}-{self.entity_description.key}"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.lastest_time


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmberConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    description = SensorEntityDescription(
        key="usages-latest-time",
        name=f"{entry.title} usages latest time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-end",
    )
    entity = AmberUsagesLatestDataSensor(coordinator, description)

    async_add_entities([entity])
