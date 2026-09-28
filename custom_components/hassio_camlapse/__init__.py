"""The Hassio Timelapse integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import DOMAIN
from .timelapse import TimelapseManager
from .validation import validate_numeric_config
import datetime

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hassio CamLapse from a config entry."""
    _LOGGER.info("Setting up Hassio CamLapse entry: %s", entry.title)

    hass.data.setdefault(DOMAIN, {})

    try:
        config = validate_numeric_config(entry.data)
    except vol.Invalid as err:
        raise ConfigEntryError(f"Invalid {err.path[0]}: {err.msg}. Reconfigure this CamLapse entry.") from err

    manager = TimelapseManager(hass, config)
    hass.data[DOMAIN][entry.entry_id] = manager

    async def hourly_maintenance(now):
        await manager.check_and_generate_backlog()
        await manager.cleanup_old_files()

    from homeassistant.helpers.event import async_track_time_interval

    # Run hourly
    entry.async_on_unload(async_track_time_interval(hass, hourly_maintenance, datetime.timedelta(hours=1)))

    # Run immediately
    hass.async_create_task(hourly_maintenance(None))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Hassio Timelapse entry: %s", entry.title)

    # Unload entities first so RestoreEntity stores the pre-unload on/off state.
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    if manager := hass.data[DOMAIN].pop(entry.entry_id, None):
        await manager.stop()
    return True
