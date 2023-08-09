"""Support for Amber Electric - Usages."""

from amberelectric import Configuration
from amberelectric.api import amber_api

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from .const import CONF_SITE_ID, DOMAIN
from .coordinator import AmberUsagesCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amber Electric from a config entry."""
    configuration = Configuration(access_token=entry.data[CONF_API_TOKEN])
    api_instance = amber_api.AmberApi.create(configuration)
    site_id = entry.data[CONF_SITE_ID]

    usages_coordinator = AmberUsagesCoordinator(
        hass, api_instance, site_id, entry.title
    )
    await usages_coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = usages_coordinator
    return True
