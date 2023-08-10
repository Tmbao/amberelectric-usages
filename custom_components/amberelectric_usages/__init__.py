"""Support for Amber Electric - Usages."""

from amberelectric import Configuration
from amberelectric.api import amber_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from .const import CONF_SITE_ID, DOMAIN, PLATFORMS
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
    hass.setdefault(DOMAIN, {})[entry.entry_id] = usages_coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
