from pathlib import Path

from pydoover import config


ENTITY_PATTERN = r"^[a-z_]+\.[a-z0-9_]+$"


class NamedEntity(config.Object):
    entity_id = config.String(
        "Entity ID",
        name="entity_id",
        pattern=ENTITY_PATTERN,
        description="Home Assistant entity ID, for example sensor.lounge_temperature.",
    )
    display_name = config.String(
        "Display Name",
        name="display_name",
        default="",
        description="Optional label in Doover. The entity ID is used when blank.",
    )


class NumericSensor(config.Object):
    entity_id = config.String(
        "Entity ID",
        name="entity_id",
        pattern=ENTITY_PATTERN,
        description="Home Assistant entity ID, for example sensor.lounge_temperature.",
    )
    display_name = config.String(
        "Display Name",
        name="display_name",
        default="",
        description="Optional label in Doover. The entity ID is used when blank.",
    )
    units = config.String(
        "Units",
        name="units",
        default="",
        description="Optional engineering units shown in Doover.",
    )
    precision = config.Integer(
        "Decimal Places",
        name="precision",
        default=2,
        minimum=0,
        maximum=8,
    )


class HomeAssistantBridgeConfig(config.Schema):
    bridge_token = config.String(
        "Home Assistant Bridge Credential",
        name="bridge_token",
        format="password",
        description="The same random value configured in the Home Assistant Doover Device app.",
    )
    poll_interval = config.Number(
        "Polling Interval",
        name="poll_interval",
        default=2.0,
        minimum=1.0,
        maximum=300.0,
        description="Seconds between Home Assistant state reads.",
    )
    numeric_sensors = config.Array(
        "Numeric Sensors",
        element=NumericSensor("Numeric Sensor", additional_elements=False),
        default=[],
        max_items=100,
    )
    text_sensors = config.Array(
        "Text Sensors",
        element=NamedEntity("Text Sensor", additional_elements=False),
        default=[],
        max_items=100,
    )
    binary_sensors = config.Array(
        "Binary Sensors",
        element=NamedEntity("Binary Sensor", additional_elements=False),
        default=[],
        max_items=100,
    )
    lights = config.Array(
        "Lights",
        element=NamedEntity("Light", additional_elements=False),
        default=[],
        max_items=100,
    )


def export() -> None:
    HomeAssistantBridgeConfig.export(
        Path(__file__).parents[2] / "doover_config.json",
        "home_assistant_bridge",
    )
