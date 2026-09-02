from __future__ import annotations

import logging
import re
from typing import Any

from pydoover import ui
from pydoover.docker import Application

from .app_config import HomeAssistantBridgeConfig
from .app_tags import HomeAssistantBridgeTags
from .app_ui import HomeAssistantBridgeUI
from .bridge_client import BridgeClient, BridgeClientError
from .model import reading_value, specs_from_config


LOGGER = logging.getLogger(__name__)
LIGHT_HANDLER = re.compile(r"^light_(on|off|toggle)__[a-z0-9_]+$")


class HomeAssistantBridgeApplication(Application):
    config_cls = HomeAssistantBridgeConfig
    tags_cls = HomeAssistantBridgeTags
    ui_cls = HomeAssistantBridgeUI

    config: HomeAssistantBridgeConfig
    tags: HomeAssistantBridgeTags

    async def _on_deployment_config_update(self, config: dict[str, Any]) -> None:
        """Load deployment config without logging the bridge credential."""
        try:
            app_config = config["applications"][self.app_key]
        except KeyError:
            LOGGER.warning(
                "Application key %s is missing from deployment config", self.app_key
            )
            app_config = {}
        self.device_agent.agent_id = app_config.get("AGENT_ID")
        self.app_display_name = app_config.get("APP_DISPLAY_NAME", "")
        LOGGER.info("Home Assistant bridge deployment configuration updated")
        self.config._inject_deployment_config(app_config)

    async def setup(self) -> None:
        self.specs = specs_from_config(self.config)
        self.spec_by_key = {spec.key: spec for spec in self.specs}
        self.client = BridgeClient(self.config.bridge_token.value)
        self.loop_target_period = self.config.poll_interval.value

    async def main_loop(self) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        try:
            response = await self.client.query_entities(
                [spec.entity_id for spec in self.specs]
            )
            readings = {
                item.get("entity_id"): item
                for item in response.get("entities", [])
                if isinstance(item, dict)
            }
            for spec in self.specs:
                reading = readings.get(spec.entity_id)
                available, value = reading_value(
                    spec, reading.get("state") if reading else None
                )
                await self.tags.get_tag(spec.available_tag).set(available)
                if available:
                    await self.tags.get_tag(spec.value_tag).set(value)
            await self.tags.bridge_connected.set(True)
            await self.tags.last_error.set("")
        except BridgeClientError as exc:
            await self.tags.bridge_connected.set(False)
            await self.tags.last_error.set(str(exc))
            LOGGER.warning("Home Assistant bridge read failed: %s", exc)

    @ui.handler(LIGHT_HANDLER, auto_update=False)
    async def handle_light_command(self, ctx, _payload) -> dict[str, str]:
        prefix, key = ctx.method.split("__", 1)
        action = prefix.removeprefix("light_")
        command = {"on": "turn_on", "off": "turn_off", "toggle": "toggle"}[action]
        spec = self.spec_by_key.get(key)
        if spec is None or spec.kind != "light":
            raise ValueError("Unknown configured light")
        try:
            await self.client.command_light(spec.entity_id, command)
            await self._refresh()
        except BridgeClientError as exc:
            await self.tags.bridge_connected.set(False)
            await self.tags.last_error.set(str(exc))
            raise
        return {"entity_id": spec.entity_id, "command": command}
