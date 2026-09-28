"""Test fixtures using Home Assistant's real config entry implementation."""

import os

# HA's cloud dependency imports LiteLLM; tests must not fetch its price metadata.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from types import MappingProxyType
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.hassio_camlapse.const import DOMAIN
from custom_components.hassio_camlapse.config_flow import ConfigFlow
from custom_components.hassio_camlapse.validation import validate_numeric_config


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    # Reconfiguration should request a reload, not start cameras in these tests.
    with patch.object(instance.config_entries, "async_schedule_reload"):
        yield instance
    await instance.async_stop(force=True)


@pytest.fixture
def config():
    return validate_numeric_config(
        {
            "camera_entity_id": "camera.garden",
            "snapshot_path": "/media/timelapse",
            "video_path": "/media/timelapse",
            "output_codec": "libx264",
        }
    )


@pytest.fixture
def add_entry(hass, config):
    def add(camera="camera.garden", unique_id=None, **overrides):
        entry = ConfigEntry(
            domain=DOMAIN,
            title=camera,
            data={**config, "camera_entity_id": camera, **overrides},
            unique_id=unique_id,
            version=1,
            minor_version=1,
            options={},
            source="user",
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        hass.config_entries._entries[entry.entry_id] = entry
        return entry

    return add


@pytest.fixture
def make_flow(hass):
    def make(entry=None):
        flow = ConfigFlow()
        flow.hass = hass
        flow.handler = DOMAIN
        flow.flow_id = "test-flow"
        flow.context = (
            {"source": "user"}
            if entry is None
            else {
                "source": "reconfigure",
                "entry_id": entry.entry_id,
            }
        )
        return flow

    return make
