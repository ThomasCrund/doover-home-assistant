from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


EntityKind = Literal["number", "text", "boolean", "light"]


@dataclass(frozen=True)
class EntitySpec:
    entity_id: str
    display_name: str
    kind: EntityKind
    precision: int = 2
    units: str = ""

    @property
    def key(self) -> str:
        return self.entity_id.replace(".", "_")

    @property
    def value_tag(self) -> str:
        return f"{self.key}_value"

    @property
    def available_tag(self) -> str:
        return f"{self.key}_available"


def _value(element: Any, name: str) -> Any:
    return getattr(element, name).value


def specs_from_config(config: Any) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    groups = (
        (config.numeric_sensors.elements, "number", "sensor."),
        (config.text_sensors.elements, "text", "sensor."),
        (config.binary_sensors.elements, "boolean", "binary_sensor."),
        (config.lights.elements, "light", "light."),
    )
    for elements, kind, required_prefix in groups:
        for element in elements:
            entity_id = _value(element, "entity_id")
            if not isinstance(entity_id, str) or not entity_id.startswith(
                required_prefix
            ):
                raise ValueError(
                    f"{entity_id!r} must be a {required_prefix.rstrip('.')} entity"
                )
            configured_name = _value(element, "display_name")
            display_name = configured_name.strip() or entity_id
            precision = _value(element, "precision") if kind == "number" else 2
            units = _value(element, "units") if kind == "number" else ""
            specs.append(
                EntitySpec(
                    entity_id=entity_id,
                    display_name=display_name,
                    kind=kind,
                    precision=precision,
                    units=units,
                )
            )

    entity_ids = [spec.entity_id for spec in specs]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("Each Home Assistant entity can be configured only once")
    if not specs:
        raise ValueError("Configure at least one Home Assistant entity")
    if len(specs) > 100:
        raise ValueError("At most 100 Home Assistant entities can be configured")
    return specs


def reading_value(spec: EntitySpec, state: Any) -> tuple[bool, Any]:
    if not isinstance(state, str) or state in {"unknown", "unavailable"}:
        return False, None
    if spec.kind == "number":
        try:
            return True, float(state)
        except ValueError:
            return False, None
    if spec.kind in {"boolean", "light"}:
        if state not in {"on", "off"}:
            return False, None
        return True, state == "on"
    return True, state
