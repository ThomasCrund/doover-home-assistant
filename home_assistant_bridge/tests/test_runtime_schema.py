from __future__ import annotations

import asyncio

from home_assistant_bridge.app_config import HomeAssistantBridgeConfig
from home_assistant_bridge.app_tags import HomeAssistantBridgeTags
from home_assistant_bridge.app_ui import HomeAssistantBridgeUI
from home_assistant_bridge.application import HomeAssistantBridgeApplication
from home_assistant_bridge.model import specs_from_config


def configured_schema() -> HomeAssistantBridgeConfig:
    config = HomeAssistantBridgeConfig()
    config._inject_deployment_config(
        {
            "bridge_token": "x" * 40,
            "poll_interval": 2.0,
            "numeric_sensors": [
                {
                    "entity_id": "sensor.lounge_temperature",
                    "display_name": "Lounge Temperature",
                    "units": "°C",
                    "precision": 1,
                }
            ],
            "text_sensors": [],
            "binary_sensors": [
                {
                    "entity_id": "binary_sensor.front_door",
                    "display_name": "Front Door",
                }
            ],
            "lights": [{"entity_id": "light.lounge", "display_name": "Lounge Light"}],
        }
    )
    return config


def test_released_pydoover_builds_dynamic_tags_and_controls():
    async def build():
        config = configured_schema()
        tags = HomeAssistantBridgeTags("home_assistant_bridge", None, config)
        await tags.setup()
        app_ui = HomeAssistantBridgeUI(config, tags, "home_assistant_bridge")
        await app_ui.setup()
        return tags.to_schema(), app_ui.to_schema()

    tags, schema = asyncio.run(build())

    assert "sensor_lounge_temperature_value" in tags
    assert tags["sensor_lounge_temperature_value"]["type"] == "number"
    assert "entity__sensor_lounge_temperature" in schema["children"]
    light = schema["children"]["entity__light_lounge"]
    assert "light_on__light_lounge" in light["children"]
    assert "light_off__light_lounge" in light["children"]
    assert "light_toggle__light_lounge" in light["children"]


def test_deployment_loader_is_overridden_to_avoid_framework_secret_logging():
    assert (
        HomeAssistantBridgeApplication._on_deployment_config_update
        is not HomeAssistantBridgeApplication.__mro__[1]._on_deployment_config_update
    )


class FakeTag:
    def __init__(self):
        self.values = []

    async def set(self, value):
        self.values.append(value)


class FakeTags:
    def __init__(self, specs):
        self.bridge_connected = FakeTag()
        self.last_error = FakeTag()
        self.dynamic = {
            name: FakeTag()
            for spec in specs
            for name in (spec.value_tag, spec.available_tag)
        }

    def get_tag(self, name):
        return self.dynamic[name]


class FakeClient:
    def __init__(self):
        self.commands = []

    async def query_entities(self, _entity_ids):
        return {
            "entities": [
                {"entity_id": "sensor.lounge_temperature", "state": "21.5"},
                {"entity_id": "binary_sensor.front_door", "state": "on"},
                {"entity_id": "light.lounge", "state": "off"},
            ],
            "missing": [],
        }

    async def command_light(self, entity_id, command):
        self.commands.append((entity_id, command))
        return {"entity_id": entity_id, "command": command}


def test_application_maps_readings_and_light_ui_commands():
    async def exercise():
        app = object.__new__(HomeAssistantBridgeApplication)
        app.specs = specs_from_config(configured_schema())
        app.spec_by_key = {spec.key: spec for spec in app.specs}
        app.tags = FakeTags(app.specs)
        app.client = FakeClient()

        await app._refresh()
        context = type("Context", (), {"method": "light_on__light_lounge"})()
        result = await app.handle_light_command(context, None)
        return app, result

    app, result = asyncio.run(exercise())

    assert app.tags.dynamic["sensor_lounge_temperature_value"].values[-1] == 21.5
    assert app.tags.dynamic["binary_sensor_front_door_value"].values[-1] is True
    assert app.tags.dynamic["light_lounge_value"].values[-1] is False
    assert app.tags.bridge_connected.values[-1] is True
    assert app.client.commands == [("light.lounge", "turn_on")]
    assert result == {"entity_id": "light.lounge", "command": "turn_on"}
