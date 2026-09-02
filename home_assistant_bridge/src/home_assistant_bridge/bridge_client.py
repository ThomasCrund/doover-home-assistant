from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any


BRIDGE_URL = "http://127.0.0.1:49192"


class BridgeClientError(Exception):
    pass


class BridgeClient:
    def __init__(self, token: str, timeout: float = 10.0):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("Bridge credential must contain at least 32 characters")
        self._token = token
        self._timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{BRIDGE_URL}{path}",
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get("error", "request rejected")
            except (json.JSONDecodeError, AttributeError):
                detail = "request rejected"
            raise BridgeClientError(
                f"Bridge returned HTTP {exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            detail = getattr(exc, "reason", str(exc))
            raise BridgeClientError(f"Bridge is unavailable: {detail}") from exc
        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise BridgeClientError("Bridge returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise BridgeClientError("Bridge returned an invalid response")
        return result

    async def query_entities(self, entity_ids: list[str]) -> dict[str, Any]:
        result = await asyncio.to_thread(
            self._post, "/v1/entities/query", {"entity_ids": entity_ids}
        )
        entities = result.get("entities")
        missing = result.get("missing")
        if not isinstance(entities, list) or not isinstance(missing, list):
            raise BridgeClientError("Bridge returned an invalid entity response")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("entity_id"), str)
            or not isinstance(item.get("state"), str)
            for item in entities
        ):
            raise BridgeClientError("Bridge returned an invalid entity reading")
        return result

    async def command_light(self, entity_id: str, command: str) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._post,
            "/v1/commands",
            {"entity_id": entity_id, "command": command},
        )
