"""Support for Amber Electric - Usages."""

import amberelectric

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from .const import CONF_SITE_ID, PLATFORMS
from .coordinator import AmberUsagesCoordinator

type AmberConfigEntry = ConfigEntry[AmberUsagesCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AmberConfigEntry) -> bool:
    """Set up Amber Electric from a config entry."""
    configuration = amberelectric.Configuration(access_token=entry.data[CONF_API_TOKEN])
    api_client = amberelectric.ApiClient(configuration)
    api_instance = amberelectric.AmberApi(api_client)
    site_id = entry.data[CONF_SITE_ID]

    usages_coordinator = AmberUsagesCoordinator(
        hass, api_instance, site_id, entry.title
    )
    await usages_coordinator.async_config_entry_first_refresh()
    entry.runtime_data = usages_coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AmberConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
