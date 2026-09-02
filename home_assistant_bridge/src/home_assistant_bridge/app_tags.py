from pydoover.tags import Tag, Tags

from .model import specs_from_config


class HomeAssistantBridgeTags(Tags):
    bridge_connected = Tag("boolean", default=False)
    last_error = Tag("string", default="")

    async def setup(self) -> None:
        for spec in specs_from_config(self.config):
            tag_type = {
                "number": "number",
                "text": "string",
                "boolean": "boolean",
                "light": "boolean",
            }[spec.kind]
            self.add_tag(spec.value_tag, Tag(tag_type))
            self.add_tag(spec.available_tag, Tag("boolean", default=False))
