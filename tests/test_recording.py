"""Recording controls, restored state and safe timer lifecycle."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import State
from homeassistant.helpers import restore_state

from custom_components.hassio_camlapse import async_unload_entry
from custom_components.hassio_camlapse.const import DOMAIN
from custom_components.hassio_camlapse.switch import RecordingSwitch, async_setup_entry
from custom_components.hassio_camlapse.timelapse import TimelapseManager


@pytest.fixture
def manager(hass, config):
    return TimelapseManager(hass, config)


@pytest.fixture
def timer():
    with patch("custom_components.hassio_camlapse.timelapse.async_track_time_interval") as schedule:
        yield schedule


async def test_repeated_start_stop_does_not_duplicate_timers(manager, timer):
    await manager.start()
    await manager.start()
    timer.assert_called_once()
    assert manager.is_recording
    await manager.stop()
    await manager.stop()
    timer.return_value.assert_called_once()
    assert not manager.is_recording
    await manager.start()
    assert timer.call_count == 2
    await manager.stop()


async def test_queued_snapshot_is_skipped_after_stop(manager, timer):
    with patch.object(manager.snapshot_service, "async_take_snapshot", new_callable=AsyncMock) as take:
        await manager.start()
        await timer.call_args.args[1](datetime.now(timezone.utc))
        take.assert_awaited_once()
        await manager.stop()
        await timer.call_args.args[1](datetime.now(timezone.utc))
        take.assert_awaited_once()


@pytest.mark.parametrize("previous,expected", [(None, True), ("on", True), ("off", False)])
async def test_restore_before_scheduling(hass, add_entry, manager, timer, previous, expected):
    entity = RecordingSwitch(add_entry(), manager)
    entity.hass = hass
    entity.entity_id = "switch.garden_camlapse_recording"
    if previous is not None:
        restore_state.async_get(hass).last_states[entity.entity_id] = restore_state.StoredState(
            State(entity.entity_id, previous), None, datetime.now(timezone.utc)
        )
    await entity.async_added_to_hass()
    assert entity.is_on is expected
    assert timer.call_count == int(expected)
    await manager.stop()


async def test_switch_actions_control_only_its_camera(hass, add_entry, manager, timer, config):
    first = RecordingSwitch(add_entry(), manager)
    other_manager = TimelapseManager(hass, {**config, "camera_entity_id": "camera.other"})
    other = RecordingSwitch(add_entry("camera.other"), other_manager)
    with patch.object(first, "async_write_ha_state"), patch.object(other, "async_write_ha_state"):
        await first.async_turn_on()
        await other.async_turn_on()
        await first.async_turn_off()
        assert not first.is_on
        assert other.is_on
        await other.async_turn_off()


@pytest.mark.parametrize("enabled", [True, False])
async def test_entity_removal_preserves_state_for_reload(hass, add_entry, manager, timer, enabled):
    entry = add_entry()
    entity = RecordingSwitch(entry, manager)
    entity.hass = hass
    entity.entity_id = "switch.garden_camlapse_recording"
    restore_state.async_get(hass).async_restore_entity_added(entity)
    if enabled:
        await manager.start()
    hass.states.async_set(entity.entity_id, "on" if enabled else "off")
    # The actual HA removal order: internal restore hook, then integration hook.
    await entity.async_internal_will_remove_from_hass()
    await entity.async_will_remove_from_hass()
    assert not manager.is_recording
    replacement = RecordingSwitch(entry, manager)
    replacement.hass = hass
    replacement.entity_id = entity.entity_id
    await replacement.async_added_to_hass()
    assert replacement.is_on is enabled
    await manager.stop()


async def test_platform_exposes_stable_unique_switch(hass, add_entry, manager):
    entry = add_entry()
    hass.data[DOMAIN] = {entry.entry_id: manager}
    add = Mock()
    await async_setup_entry(hass, entry, add)
    entity = add.call_args.args[0][0]
    assert isinstance(entity, RecordingSwitch)
    assert entity.unique_id == f"{entry.entry_id}_recording"
    assert not manager.is_recording


async def test_failed_platform_unload_keeps_manager(hass, add_entry, manager, timer):
    entry = add_entry()
    hass.data[DOMAIN] = {entry.entry_id: manager}
    await manager.start()
    with patch.object(hass.config_entries, "async_unload_platforms", return_value=False):
        assert not await async_unload_entry(hass, entry)
    assert hass.data[DOMAIN][entry.entry_id] is manager
    assert manager.is_recording
    await manager.stop()


async def test_successful_unload_stops_manager_after_platform(hass, add_entry, manager, timer):
    entry = add_entry()
    hass.data[DOMAIN] = {entry.entry_id: manager}
    await manager.start()

    async def unload(*args):
        assert manager.is_recording  # RestoreEntity must still see the on state.
        return True

    with patch.object(hass.config_entries, "async_unload_platforms", side_effect=unload):
        assert await async_unload_entry(hass, entry)
    assert not manager.is_recording
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_paused_camera_still_processes_backlog_and_retention(manager):
    assert not manager.is_recording
    with (
        patch.object(manager.video_service, "check_and_generate_backlog", new_callable=AsyncMock) as backlog,
        patch.object(manager.cleanup_service, "cleanup_old_files", new_callable=AsyncMock) as cleanup,
    ):
        await manager.check_and_generate_backlog()
        await manager.cleanup_old_files()
    backlog.assert_awaited_once_with(manager.video_retention_days)
    cleanup.assert_awaited_once()


async def test_old_timer_cannot_capture_after_rapid_restart(manager, timer):
    with patch.object(manager.snapshot_service, "async_take_snapshot", new_callable=AsyncMock) as take:
        await manager.start()
        old_callback = timer.call_args.args[1]
        await manager.stop()
        await manager.start()
        new_callback = timer.call_args.args[1]
        await old_callback(datetime.now(timezone.utc))
        take.assert_not_awaited()
        await new_callback(datetime.now(timezone.utc))
        take.assert_awaited_once()
        await manager.stop()
