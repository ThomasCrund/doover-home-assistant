from pathlib import Path

from pydoover import ui

from .model import EntitySpec, specs_from_config


class HomeAssistantBridgeUI(ui.UI, icon="home"):
    async def setup(self) -> None:
        self.add_element(
            ui.BooleanVariable(
                "Bridge Connected",
                name="bridge_connected",
                value=self.tags.bridge_connected,
            )
        )
        self.add_element(
            ui.TextVariable(
                "Last Error",
                name="last_error",
                value=self.tags.last_error,
            )
        )
        for spec in specs_from_config(self.config):
            self.add_element(self._entity_module(spec))

    def _entity_module(self, spec: EntitySpec) -> ui.Submodule:
        value_tag = self.tags.get_tag(spec.value_tag)
        available_tag = self.tags.get_tag(spec.available_tag)
        if spec.kind == "number":
            reading = ui.NumericVariable(
                "Reading",
                name=f"{spec.key}_reading",
                value=value_tag,
                precision=spec.precision,
                units=spec.units,
            )
        elif spec.kind == "text":
            reading = ui.TextVariable(
                "Reading", name=f"{spec.key}_reading", value=value_tag
            )
        else:
            reading = ui.BooleanVariable(
                "State", name=f"{spec.key}_state", value=value_tag
            )

        children = [
            ui.BooleanVariable(
                "Available",
                name=f"{spec.key}_available",
                value=available_tag,
            ),
            reading,
        ]
        if spec.kind == "light":
            children.extend(
                [
                    ui.Button("Turn On", name=f"light_on__{spec.key}"),
                    ui.Button("Turn Off", name=f"light_off__{spec.key}"),
                    ui.Button("Toggle", name=f"light_toggle__{spec.key}"),
                ]
            )
        return ui.Submodule(
            spec.display_name,
            name=f"entity__{spec.key}",
            children=children,
            is_collapsed=False,
        )


def export() -> None:
    HomeAssistantBridgeUI(None, None, None).export(
        Path(__file__).parents[2] / "doover_config.json",
        "home_assistant_bridge",
    )
