"""Per-camera recording control for dashboards and automations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .timelapse import TimelapseManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Expose one recording switch for each configured camera."""
    async_add_entities([RecordingSwitch(entry, hass.data[DOMAIN][entry.entry_id])])


class RecordingSwitch(SwitchEntity, RestoreEntity):
    """Pause new snapshots while retaining processing and retention cleanup."""

    _attr_should_poll = False
    _attr_icon = "mdi:timelapse"

    def __init__(self, entry: ConfigEntry, manager: TimelapseManager) -> None:
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_recording"
        self._attr_name = f"{entry.title} CamLapse recording"

    @property
    def is_on(self) -> bool:
        """Report whether periodic snapshots are enabled."""
        return self._manager.is_recording

    async def async_added_to_hass(self) -> None:
        """Restore a paused camera before starting any snapshot timer."""
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        # Preserve the original always-on behavior for new/upgraded entries.
        if previous is None or previous.state != STATE_OFF:
            await self._manager.start()

    async def async_will_remove_from_hass(self) -> None:
        """Remember the switch state before cancelling its timer."""
        await super().async_will_remove_from_hass()
        await self._manager.stop()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume snapshots at the configured interval."""
        await self._manager.start()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop scheduling snapshots; an in-flight snapshot may finish."""
        await self._manager.stop()
        self.async_write_ha_state()
