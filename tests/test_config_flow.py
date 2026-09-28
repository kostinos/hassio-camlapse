"""Regression coverage for validation, serialized forms and camera identity."""

import pytest
import voluptuous as vol
import voluptuous_serialize
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import ConfigEntryError
from unittest.mock import patch

from custom_components.hassio_camlapse import async_setup_entry
from custom_components.hassio_camlapse.config_flow import _schema
from custom_components.hassio_camlapse.validation import NUMERIC_FIELDS, validate_numeric_config


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize("bad", [0, -1, 1.5, True, False, "2", None, float("nan"), float("inf"), float("-inf")])
def test_invalid_numbers(config, field, bad):
    with pytest.raises(vol.Invalid):
        validate_numeric_config({**config, field: bad})


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
def test_boundaries(config, field):
    minimum, maximum, _, _ = NUMERIC_FIELDS[field]
    for value in (minimum, maximum, float(maximum)):
        result = validate_numeric_config({**config, field: value})
        assert result[field] == value
        assert type(result[field]) is int
    with pytest.raises(vol.Invalid):
        validate_numeric_config({**config, field: maximum + 1})


def test_schema_serializes_number_boxes():
    fields = voluptuous_serialize.convert(_schema({}), custom_serializer=cv.custom_serializer)
    by_name = {field["name"]: field for field in fields}
    for name, (minimum, maximum, _, _) in NUMERIC_FIELDS.items():
        number = by_name[name]["selector"]["number"]
        assert number["min"] == minimum
        assert number["max"] == maximum
        assert number["step"] == 1
        assert number["mode"] == "box"


async def test_create_entry(make_flow, config):
    flow = make_flow()
    result = await flow.async_step_user({**config, "output_fps": 10.0})
    assert result["type"] == "create_entry"
    assert result["data"]["output_fps"] == 10
    assert type(result["data"]["output_fps"]) is int
    assert flow.unique_id == "camera.garden"


@pytest.mark.parametrize("unique_id", [None, "camera.garden"])
async def test_duplicate_creation_including_legacy(make_flow, add_entry, config, unique_id):
    add_entry(unique_id=unique_id)
    result = await make_flow().async_step_user(config)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_invalid_creation_returns_field_error(make_flow, config):
    result = await make_flow().async_step_user({**config, "output_fps": 0})
    assert result["type"] == "form"
    assert result["errors"] == {"output_fps": "invalid_number"}


@pytest.mark.parametrize("unique_id", [None, "camera.other"])
async def test_reconfigure_rejects_duplicate(make_flow, add_entry, config, unique_id):
    entry = add_entry(unique_id="camera.garden")
    add_entry("camera.other", unique_id=unique_id)
    result = await make_flow(entry).async_step_reconfigure({**config, "camera_entity_id": "camera.other"})
    assert result["errors"] == {"camera_entity_id": "already_configured"}
    assert entry.data["camera_entity_id"] == entry.unique_id == "camera.garden"


@pytest.mark.parametrize("camera", ["camera.garden", "camera.new"])
async def test_reconfigure_legacy_assigns_identity(make_flow, add_entry, config, camera):
    entry = add_entry()
    result = await make_flow(entry).async_step_reconfigure({**config, "camera_entity_id": camera})
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["camera_entity_id"] == entry.unique_id == entry.title == camera


async def test_changing_camera_releases_old_identity(make_flow, add_entry, config):
    entry = add_entry(unique_id="camera.garden")
    await make_flow(entry).async_step_reconfigure({**config, "camera_entity_id": "camera.new"})
    assert (await make_flow().async_step_user(config))["type"] == "create_entry"
    result = await make_flow().async_step_user({**config, "camera_entity_id": "camera.new"})
    assert result["reason"] == "already_configured"


async def test_invalid_reconfigure_preserves_entry(make_flow, add_entry, config):
    entry = add_entry()
    before = dict(entry.data)
    result = await make_flow(entry).async_step_reconfigure({**config, "interval_seconds": -1})
    assert result["errors"] == {"interval_seconds": "invalid_number"}
    assert dict(entry.data) == before
    assert entry.unique_id is None


async def test_old_invalid_entry_stops_before_manager(hass, add_entry):
    entry = add_entry(output_fps=0)
    with patch("custom_components.hassio_camlapse.TimelapseManager") as manager:
        with pytest.raises(ConfigEntryError, match="output_fps.*Reconfigure"):
            await async_setup_entry(hass, entry)
        manager.assert_not_called()
